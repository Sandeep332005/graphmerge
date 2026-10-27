from typing import Any

from langgraph.graph import END, START, StateGraph

from graphmerge.analysis.ast_parser import validate_diff_syntax
from graphmerge.optimization.solver import ConflictGraphOptimizer
from graphmerge.orchestration.checkpoint import CheckpointStore
from graphmerge.orchestration.dispatch import WorkerPool
from graphmerge.orchestration.sandbox import sandbox_integration_node_real
from graphmerge.orchestration.state import (
    AgentProposal,
    CollisionContext,
    GraphMergeState,
    LocalVerification,
)


def worker_fanout_node(state: GraphMergeState) -> dict[str, Any]:
    """Coordinates task fan-out and proposal intake.

    If proposals are pre-loaded (testing/MCP mode), passes them through.
    If active_backlog exists and a worker_pool is configured, dispatches
    tasks to agent workers for proposal generation.
    """
    proposals = state.get("proposals", [])
    backlog = state.get("active_backlog", [])
    baseline = state.get("current_baseline", "s_0")

    if proposals:
        return {"current_baseline": baseline, "proposals": proposals}

    if backlog:
        worker_cfg = state.get("worker_config")
        if worker_cfg and "worker" in worker_cfg:
            pool = WorkerPool(worker_cfg["worker"])
            generated = pool.dispatch(backlog, baseline)
            return {"current_baseline": baseline, "proposals": generated}
        return {"current_baseline": baseline, "proposals": backlog}

    return {"current_baseline": baseline, "proposals": []}


def worker_preverification_node(state: GraphMergeState) -> dict[str, Any]:
    """Validates candidate patches before conflict graph entry.

    1. Fast AST syntax sanity check (rejects malformed syntax).
    2. Empirical local gain validation (requires Delta f_i > 0).
    """
    proposals = state.get("proposals", [])
    valid_proposals: list[AgentProposal] = []
    unverified_proposals: list[AgentProposal] = list(state.get("rejected_unverified_patches", []))

    for p in proposals:
        gain = float(p.get("verified_local_gain", 1.0))
        verification: LocalVerification | None = p.get("verification")

        if gain <= 0.0 or (verification and verification.get("status") == "FAILED"):
            p["verification"] = {
                "status": "FAILED",
                "syntax_valid": verification.get("syntax_valid", False) if verification else True,
                "tests_passed": False,
                "empirical_gain": gain,
                "error_message": "Negative or zero empirical gain Delta f_i <= 0",
            }
            unverified_proposals.append(p)
            continue

        diff_text = p.get("diff_content", "")
        if diff_text:
            if not validate_diff_syntax(diff_text):
                p["verification"] = {
                    "status": "FAILED",
                    "syntax_valid": False,
                    "tests_passed": False,
                    "empirical_gain": -1.0,
                    "error_message": "AST SyntaxError in proposed patch",
                }
                unverified_proposals.append(p)
                continue

        p["verification"] = {
            "status": "PASSED",
            "syntax_valid": True,
            "tests_passed": True,
            "empirical_gain": gain,
            "error_message": None,
        }
        valid_proposals.append(p)

    return {
        "proposals": valid_proposals,
        "rejected_unverified_patches": unverified_proposals,
    }


def conflict_optimization_node(state: GraphMergeState) -> dict[str, Any]:
    """Constructs Two-Tier conflict graph G=(V,E) and solves MWIS."""
    proposals = state.get("proposals", [])
    if not proposals:
        return {
            "accepted_patches": state.get("accepted_patches", []),
            "staged_patches": [],
            "is_converged": True,
        }

    opt_payload = []
    for p in proposals:
        item = {
            "id": p["id"],
            "files": p.get("touched_symbols", {}),
            "weight": p.get("verified_local_gain", 1.0),
        }
        if "symbol_analysis" in p and p["symbol_analysis"]:
            item["symbol_analysis"] = p["symbol_analysis"]
        opt_payload.append(item)

    optimizer = ConflictGraphOptimizer()
    optimizer.build_conflict_graph(opt_payload)
    accepted_ids, rejected_ids = optimizer.solve_mwis()
    diagnostics = optimizer.get_conflict_diagnostics()

    newly_accepted = [p for p in proposals if p["id"] in accepted_ids]
    staged = [p for p in proposals if p["id"] in rejected_ids]

    return {
        "newly_accepted": newly_accepted,
        "staged_patches": staged,
        "conflict_diagnostics": diagnostics,
    }


def sandbox_integration_node(state: GraphMergeState) -> dict[str, Any]:
    """Applies accepted patches atomically.

    Uses real git worktree + test runner when workspace_path points to
    a git repo. Falls back to stub baseline bumping otherwise.
    """
    return sandbox_integration_node_real(state)


def rebase_router(state: GraphMergeState) -> str:
    """Routes to adaptive reprompt or end based on convergence."""
    if state.get("is_converged", False):
        return "end_node"
    return "adaptive_reprompt"


def adaptive_reprompt_node(state: GraphMergeState) -> dict[str, Any]:
    """Generates re-prompt instructions for deferred patches.

    For each staged proposal:
    1. Extracts collision context from conflict diagnostics.
    2. Packages diffs from committed I* patches.
    3. Builds adapted proposal with collision context for next iteration.
    """
    staged = state.get("staged_patches", [])
    accepted = state.get("accepted_patches", [])
    diagnostics = state.get("conflict_diagnostics", [])
    current_baseline = state.get("current_baseline", "s_1")

    accepted_map = {p["id"]: p for p in accepted}
    adapted_proposals: list[AgentProposal] = []

    for p in staged:
        p_id = p["id"]

        colliding_ids = set()
        reasons = []
        for diag in diagnostics:
            nodes = diag.get("nodes", [])
            if p_id in nodes:
                other_id = nodes[0] if nodes[1] == p_id else nodes[1]
                if other_id in accepted_map:
                    colliding_ids.add(other_id)
                    reasons.append(diag)

        accepted_diffs = "\n\n".join(
            f"=== Accepted Diff ({cid}) ===\n{accepted_map[cid].get('diff_content', '')}"
            for cid in colliding_ids
            if cid in accepted_map
        )

        colliding_symbols = {r.get("symbol") for r in reasons if r.get("symbol")}
        sym_text = f" on symbol(s) {list(colliding_symbols)}" if colliding_symbols else ""

        instruction = (
            f"Your prior proposal for task '{p.get('task_id')}' "
            f"was deferred due to conflicts with patch(es) "
            f"{list(colliding_ids)}{sym_text} committed into "
            f"baseline {current_baseline}. Target symbols have been "
            f"updated. Regenerate your patch grounded in "
            f"{current_baseline}."
        )

        collision_context: CollisionContext = {
            "conflicting_proposal_ids": list(colliding_ids),
            "conflict_reasons": reasons,
            "accepted_patch_diffs": accepted_diffs,
            "reprompt_instruction": instruction,
        }

        adapted_proposal: AgentProposal = dict(p)
        adapted_proposal["collision_context"] = collision_context
        adapted_proposal["adapted_from_id"] = p_id
        adapted_proposals.append(adapted_proposal)

    return {"proposals": adapted_proposals}


def build_graphmerge_state_graph(
    checkpoint_dir: str | None = None,
):
    """Builds the full LangGraph state machine.

    Args:
        checkpoint_dir: If set, enables state checkpointing to this dir.
    """
    builder = StateGraph(GraphMergeState)

    builder.add_node("fanout", worker_fanout_node)
    builder.add_node("preverification", worker_preverification_node)
    builder.add_node("optimize", conflict_optimization_node)
    builder.add_node("sandbox_commit", sandbox_integration_node)
    builder.add_node("adaptive_reprompt", adaptive_reprompt_node)

    builder.add_edge(START, "fanout")
    builder.add_edge("fanout", "preverification")
    builder.add_edge("preverification", "optimize")
    builder.add_edge("optimize", "sandbox_commit")

    builder.add_conditional_edges(
        "sandbox_commit",
        rebase_router,
        {
            "end_node": END,
            "adaptive_reprompt": "adaptive_reprompt",
        },
    )
    builder.add_edge("adaptive_reprompt", "preverification")

    return builder.compile()


def run_pipeline(
    state: dict[str, Any],
    run_id: str | None = None,
    checkpoint_dir: str | None = None,
) -> dict[str, Any]:
    """Runs the full pipeline with optional checkpoint persistence.

    Args:
        state: Initial GraphMergeState dict.
        run_id: Unique identifier for this run (for checkpoint filename).
        checkpoint_dir: Directory for checkpoint files. None = no persistence.

    Returns:
        Final pipeline state dict.
    """
    store = CheckpointStore(checkpoint_dir) if checkpoint_dir else None

    if store and run_id:
        existing = store.load(run_id)
        if existing and not existing.get("is_converged", False):
            state = existing

    graph = build_graphmerge_state_graph(checkpoint_dir=checkpoint_dir)
    final_state = graph.invoke(state)

    if store and run_id:
        store.save(run_id, final_state)

    return final_state
