import argparse
import json
import sys

from graphmerge.mcp_server import (
    arbitrate_diff_patches_core,
    arbitrate_merge_proposals,
    check_patch_collision_core,
    json_default,
)


def main():
    parser = argparse.ArgumentParser(
        prog="graphmerge",
        description=("GraphMerge: AST conflict arbitration " "for parallel AI agent patches"),
    )
    sub = parser.add_subparsers(dest="command")

    arb = sub.add_parser("arbitrate", help="Arbitrate diff patches from a JSON file")
    arb.add_argument("file", help="JSON file with array of {id, diff, weight} objects")

    col = sub.add_parser("check", help="Check collision between two diff files")
    col.add_argument("diff_a", help="Path to first unified diff")
    col.add_argument("diff_b", help="Path to second unified diff")

    sub.add_parser("serve", help="Start the MCP stdio server")

    run_p = sub.add_parser(
        "run",
        help="Run full pipeline with sandbox/checkpoint support",
    )
    run_p.add_argument("file", help="JSON file with array of patch proposals")
    run_p.add_argument("--workspace", help="Git repo path for sandbox execution")
    run_p.add_argument("--test-command", help="Test command to run after applying patches")
    run_p.add_argument("--checkpoint-dir", help="Directory for checkpoint persistence")
    run_p.add_argument("--run-id", help="Run ID for checkpoint resume")
    run_p.add_argument("--max-iterations", type=int, default=3, help="Max rebase iterations")

    pipe_p = sub.add_parser(
        "pipe",
        help="JSON pipe mode: read from stdin, write to stdout",
    )
    pipe_p.add_argument(
        "--stream",
        action="store_true",
        help="JSONL streaming: one JSON object per line",
    )

    args = parser.parse_args()

    if args.command == "arbitrate":
        with open(args.file, encoding="utf-8") as f:
            patches = json.load(f)
        if all("diff" in p or "diff_content" in p for p in patches):
            result = arbitrate_diff_patches_core(patches)
        else:
            result = arbitrate_merge_proposals(patches)
        print(json.dumps(result, indent=2, default=json_default))

    elif args.command == "check":
        with open(args.diff_a, encoding="utf-8") as f:
            diff_a = f.read()
        with open(args.diff_b, encoding="utf-8") as f:
            diff_b = f.read()
        result = check_patch_collision_core(diff_a, diff_b)
        print(json.dumps(result, indent=2, default=json_default))

    elif args.command == "run":
        _run_pipeline(args)

    elif args.command == "serve":
        from graphmerge.mcp_server import main as serve_main

        serve_main()

    elif args.command == "pipe":
        _run_pipe(stream=args.stream)

    else:
        parser.print_help()
        sys.exit(1)


def _run_pipeline(args):
    """Runs the full GraphMerge pipeline via CLI."""
    from graphmerge.orchestration.supervisor import run_pipeline

    with open(args.file, encoding="utf-8") as f:
        patches = json.load(f)

    proposals = []
    for p in patches:
        proposal = {
            "id": p.get("id", f"p{len(proposals)}"),
            "diff_content": p.get("diff", p.get("diff_content", "")),
            "verified_local_gain": float(p.get("weight", p.get("verified_local_gain", 1.0))),
            "touched_symbols": p.get("touched_symbols", {}),
            "target_files": p.get("target_files", []),
        }
        proposals.append(proposal)

    state = {
        "proposals": proposals,
        "current_baseline": "s_0",
        "iteration": 0,
        "max_iterations": args.max_iterations,
        "accepted_patches": [],
        "staged_patches": [],
        "rejected_unverified_patches": [],
    }
    if args.workspace:
        state["workspace_path"] = args.workspace
    if args.test_command:
        state["test_command"] = args.test_command

    result = run_pipeline(
        state,
        run_id=args.run_id,
        checkpoint_dir=args.checkpoint_dir,
    )
    print(json.dumps(result, indent=2, default=json_default))


def _run_pipe(stream: bool = False):
    """JSON pipe mode for agent integration.

    Without --stream: reads entire stdin as one JSON object, processes,
    writes result to stdout.

    With --stream: reads one JSON object per line (JSONL), processes
    each, writes one result per line. Agents can feed patches
    continuously.

    Input format (each object):
      {"action": "arbitrate", "patches": [...]}
      {"action": "check", "diff_a": "...", "diff_b": "..."}
      {"action": "solve", "proposals": [...]}

    Defaults to "arbitrate" if no action specified but patches present.
    """
    if stream:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                result = _dispatch_pipe(req)
                print(
                    json.dumps(result, default=json_default),
                    flush=True,
                )
            except json.JSONDecodeError as e:
                print(
                    json.dumps({"status": "error", "message": str(e)}),
                    flush=True,
                )
    else:
        raw = sys.stdin.read()
        try:
            req = json.loads(raw)
            result = _dispatch_pipe(req)
            print(json.dumps(result, indent=2, default=json_default))
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)


def _dispatch_pipe(req: dict) -> dict:
    """Routes a pipe request to the appropriate core function."""
    action = req.get("action", "")

    if action == "check":
        return check_patch_collision_core(
            req["diff_a"],
            req["diff_b"],
            req.get("id_a", "patch_a"),
            req.get("id_b", "patch_b"),
        )
    elif action == "solve":
        return arbitrate_merge_proposals(req["proposals"])
    elif action == "arbitrate" or ("patches" in req):
        patches = req.get("patches", req.get("diffs", []))
        return arbitrate_diff_patches_core(patches)
    else:
        return {
            "status": "error",
            "message": (
                "Unknown action. Use: arbitrate, check, or solve. " "Or provide 'patches' array."
            ),
        }


if __name__ == "__main__":
    main()
