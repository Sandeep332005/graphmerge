import json
import logging
import sys
from typing import Any

from graphmerge.analysis.ast_parser import (
    detect_language,
    extract_hunks_per_file,
    extract_modified_lines,
    extract_symbol_analysis,
    validate_diff_syntax,
)
from graphmerge.optimization.solver import ConflictGraphOptimizer

log = logging.getLogger("graphmerge")

try:
    from mcp.server.mcpserver import MCPServer as FastMCP

    mcp = FastMCP("graphmerge-arbiter")
    HAS_MCP = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("graphmerge-arbiter")
        HAS_MCP = True
    except ImportError:
        HAS_MCP = False
        mcp = None


def arbitrate_merge_proposals(
    proposals_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Core arbitration for proposals with pre-extracted symbols."""
    optimizer = ConflictGraphOptimizer()
    g = optimizer.build_conflict_graph(proposals_data)
    accepted, rejected = optimizer.solve_mwis()
    bound = optimizer.compute_fractional_bound()
    diagnostics = optimizer.get_conflict_diagnostics()

    return {
        "status": "success",
        "accepted_proposals": list(accepted),
        "deferred_proposals": list(rejected),
        "total_nodes": g.number_of_nodes(),
        "total_conflict_edges": g.number_of_edges(),
        "conflict_diagnostics": diagnostics,
        "preservation_bound_guarantee": bound,
    }


def arbitrate_diff_patches_core(
    diff_patches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Parses raw unified diffs with multi-language AST, checks syntax,
    and runs two-tier conflict arbitration.

    Returns accepted/deferred IDs, merged_diff of accepted patches,
    and full conflict diagnostics.
    """
    proposals_payload = []
    syntax_rejected = []
    patch_diffs: dict[str, str] = {}

    for item in diff_patches:
        p_id = item.get("id", "patch")
        diff_text = item.get("diff", item.get("diff_content", ""))
        weight = float(item.get("weight", 1.0))
        task_id = item.get("task_id", p_id)

        if not validate_diff_syntax(diff_text):
            syntax_rejected.append(
                {
                    "id": p_id,
                    "task_id": task_id,
                    "reason": "Diff failed AST syntax validation",
                }
            )
            continue

        patch_diffs[p_id] = diff_text

        # Per-file language-aware symbol extraction
        lines_by_file = extract_modified_lines(diff_text)
        hunks_by_file = extract_hunks_per_file(diff_text)

        symbol_analysis: dict[str, Any] = {}
        for file_path in lines_by_file:
            lang = detect_language(file_path)
            code = hunks_by_file.get(file_path, "")
            code_bytes = code.encode("utf-8", errors="ignore")
            code_lines = list(range(1, max(2, len(code.splitlines()) + 1)))
            analysis = extract_symbol_analysis(code_bytes, code_lines, lang)
            symbol_analysis[file_path] = analysis

        if not symbol_analysis:
            # No file paths found — treat as generic snippet
            code = "\n".join(
                line[1:]
                for line in diff_text.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            )
            if code.strip():
                code_bytes = code.encode("utf-8", errors="ignore")
                code_lines = list(range(1, len(code.splitlines()) + 1))
                analysis = extract_symbol_analysis(code_bytes, code_lines)
                symbol_analysis["snippet.py"] = analysis

        proposals_payload.append(
            {
                "id": p_id,
                "task_id": task_id,
                "weight": weight,
                "symbol_analysis": symbol_analysis,
                "diff_content": diff_text,
            }
        )

    optimizer = ConflictGraphOptimizer()
    g = optimizer.build_conflict_graph(proposals_payload)
    accepted, rejected = optimizer.solve_mwis()
    bound = optimizer.compute_fractional_bound()
    diagnostics = optimizer.get_conflict_diagnostics()

    # Build merged diff of accepted patches (ordered by ID for determinism)
    accepted_list = sorted(accepted)
    merged_diff = "\n".join(patch_diffs[pid] for pid in accepted_list if pid in patch_diffs)

    return {
        "status": "success",
        "accepted_patches": accepted_list,
        "deferred_patches": sorted(rejected),
        "syntax_rejected_patches": syntax_rejected,
        "total_patches_evaluated": len(diff_patches),
        "total_conflict_edges": g.number_of_edges(),
        "conflict_diagnostics": diagnostics,
        "preservation_bound": bound,
        "merged_diff": merged_diff,
    }


def check_patch_collision_core(
    diff_a: str,
    diff_b: str,
    id_a: str = "patch_a",
    id_b: str = "patch_b",
) -> dict[str, Any]:
    """Checks whether two diffs collide under Tier 1/Tier 2 analysis."""
    res = arbitrate_diff_patches_core(
        [
            {"id": id_a, "diff": diff_a, "weight": 1.0},
            {"id": id_b, "diff": diff_b, "weight": 1.0},
        ]
    )
    has_conflict = res["total_conflict_edges"] > 0
    diagnostics = res.get("conflict_diagnostics", [])
    first_diag = diagnostics[0] if diagnostics else {}

    return {
        "has_conflict": has_conflict,
        "can_merge_concurrently": not has_conflict,
        "conflict_type": (first_diag.get("conflict_type", "NONE") if has_conflict else "NONE"),
        "tier": first_diag.get("tier", 0) if has_conflict else 0,
        "symbol": first_diag.get("symbol", "") if has_conflict else "",
        "details": first_diag,
    }


# ====================================================================
# MCP Tool Registrations
# ====================================================================
if HAS_MCP and mcp:

    @mcp.tool()
    def arbitrate_diff_patches(diffs_json: str) -> str:
        """Takes a JSON array of diff patches, extracts AST symbols with
        multi-language Tree-Sitter, detects syntactic and def-use
        conflicts, and returns the conflict-free independent set I*
        with merged_diff and preservation guarantees.
        """
        try:
            data = json.loads(diffs_json)
            result = arbitrate_diff_patches_core(data)
            log.debug(
                "arbitrate_diff_patches: %d evaluated",
                result["total_patches_evaluated"],
            )
            return json.dumps(result, indent=2, default=_json_default)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            log.warning("arbitrate_diff_patches error: %s", e)
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def check_patch_collision(
        diff_a: str,
        diff_b: str,
        id_a: str = "patch_a",
        id_b: str = "patch_b",
    ) -> str:
        """Compares two unified diffs for Tier 1/Tier 2 collisions."""
        try:
            result = check_patch_collision_core(diff_a, diff_b, id_a, id_b)
            return json.dumps(result, indent=2)
        except (ValueError, TypeError, KeyError) as e:
            log.warning("check_patch_collision error: %s", e)
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def solve_merge(proposals_json: str) -> str:
        """Takes JSON proposals with pre-extracted symbol sets and weights,
        returning the certified Maximum Weight Independent Set I*.
        """
        try:
            data = json.loads(proposals_json)
            result = arbitrate_merge_proposals(data)
            log.debug("solve_merge: %d nodes", result["total_nodes"])
            return json.dumps(result, indent=2)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            log.warning("solve_merge error: %s", e)
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def generate_reprompt_instruction(
        task_id: str,
        colliding_patch_ids: str,
        colliding_symbols: str,
        baseline_version: str = "s_1",
    ) -> str:
        """Generates a re-prompt instruction for a deferred agent."""
        instruction = (
            f"Your prior proposed patch for task '{task_id}' was deferred "
            f"by the GraphMerge coordinator due to AST symbol collisions "
            f"with patch(es) [{colliding_patch_ids}] "
            f"on symbol(s) [{colliding_symbols}]. "
            f"The accepted patch has been atomically committed "
            f"into baseline {baseline_version}. "
            f"Please regenerate your patch grounded in the updated "
            f"symbols in {baseline_version}."
        )
        return json.dumps(
            {
                "task_id": task_id,
                "target_baseline": baseline_version,
                "instruction": instruction,
            },
            indent=2,
        )


def _json_default(obj):
    """JSON serializer for set objects in symbol analysis."""
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    if HAS_MCP and mcp:
        log.info("Starting GraphMerge MCP Server (stdio transport)...")
        mcp.run()
    else:
        log.warning("MCP library not available. Running fallback CLI demo.")
        demo = [
            {"id": "p1", "files": {"math.py": ["ratio"]}, "weight": 10.0},
            {"id": "p2", "files": {"math.py": ["ratio"]}, "weight": 8.0},
            {"id": "p3", "files": {"format.py": ["iso"]}, "weight": 12.0},
        ]
        res = arbitrate_merge_proposals(demo)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
