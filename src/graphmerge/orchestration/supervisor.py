from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from graphmerge.orchestration.state import GraphMergeState
from graphmerge.optimization.solver import ConflictGraphOptimizer

optimizer = ConflictGraphOptimizer()


def worker_fanout_node(state: GraphMergeState) -> Dict[str, Any]:
    """Coordinates parallel agent task dispatch. In production runs,

    LangGraph's Send API runs concurrent LLM worker nodes.
    """
    return {"proposals": state.get("proposals", [])}


def conflict_optimization_node(state: GraphMergeState) -> Dict[str, Any]:
    """Constructs conflict graph G=(V,E) and solves Maximum Weight Independent Set."""
    proposals = state.get("proposals", [])
    if not proposals:
        return {
            "accepted_patches": [],
            "staged_patches": [],
            "is_converged": True,
        }

    # Format for optimizer
    opt_payload = [
        {
            "id": p["id"],
            "files": p.get("touched_symbols", {}),
            "weight": p.get("verified_local_gain", 1.0),
        }
        for p in proposals
    ]

    optimizer.build_conflict_graph(opt_payload)
    accepted_ids, rejected_ids = optimizer.solve_mwis()

    accepted = [p for p in proposals if p["id"] in accepted_ids]
    staged = [p for p in proposals if p["id"] in rejected_ids]

    new_iter = state.get("iteration", 0) + 1
    max_iter = state.get("max_iterations", 3)

    return {
        "accepted_patches": accepted,
        "staged_patches": staged,
        "iteration": new_iter,
        "is_converged": len(staged) == 0 or new_iter >= max_iter,
    }


def rebase_router(state: GraphMergeState) -> str:
    """Checks whether deferred patches remain to iterate in the next round."""
    if state.get("is_converged", False):
        return "end_node"
    return "rebase_and_retry"


def rebase_node(state: GraphMergeState) -> Dict[str, Any]:
    """Takes unselected/conflicted patches from the current round and stages them

    for re-evaluation against the updated baseline state.
    """
    staged = state.get("staged_patches", [])
    return {"proposals": staged}


def build_graphmerge_state_graph():
    """Builds and compiles the full LangGraph state machine."""
    builder = StateGraph(GraphMergeState)

    builder.add_node("fanout", worker_fanout_node)
    builder.add_node("optimize", conflict_optimization_node)
    builder.add_node("rebase_and_retry", rebase_node)

    builder.add_edge(START, "fanout")
    builder.add_edge("fanout", "optimize")
    builder.add_conditional_edges(
        "optimize",
        rebase_router,
        {
            "end_node": END,
            "rebase_and_retry": "rebase_and_retry",
        },
    )
    builder.add_edge("rebase_and_retry", "optimize")

    return builder.compile()
