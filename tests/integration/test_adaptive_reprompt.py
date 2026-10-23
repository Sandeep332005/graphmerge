import pytest
from graphmerge.orchestration.supervisor import build_graphmerge_state_graph
from graphmerge.orchestration.state import GraphMergeState


def test_adaptive_reprompt_collision_context_delivery():
    """Verifies that the Adaptive Re-Prompting Node delivers rich collision context

    to deferred agent workers:
    - Lists colliding accepted proposal IDs
    - Emits structured collision diagnostic metadata
    - Includes diffs from accepted proposals
    - Emits clear instructions with symbol names
    """
    app = build_graphmerge_state_graph()

    initial_state: GraphMergeState = {
        "workspace_path": "/tmp/test_workspace",
        "iteration": 0,
        "max_iterations": 3,
        "active_backlog": [],
        "proposals": [
            {
                "id": "p1",
                "task_id": "TASK-101",
                "diff_content": "def compute(x): return x * 2",
                "touched_symbols": {"engine.py": {"compute"}},
                "verified_local_gain": 10.0,
            },
            {
                "id": "p2",
                "task_id": "TASK-102",
                "diff_content": "def compute(x): return x * 3",
                "touched_symbols": {"engine.py": {"compute"}},
                "verified_local_gain": 6.0,
            },
        ],
        "accepted_patches": [],
        "staged_patches": [],
        "is_converged": False,
    }

    final_state = app.invoke(initial_state)

    # In Cycle 1: p1 is accepted (weight 10.0 > 6.0), p2 is staged.
    # In Cycle 2: p2 is re-prompted with collision context from p1, and accepted.
    assert final_state["is_converged"] is True
    assert final_state["iteration"] == 2

    accepted_patches = final_state["accepted_patches"]
    assert len(accepted_patches) == 2

    p2_accepted = next(p for p in accepted_patches if p["id"] == "p2")
    assert p2_accepted.get("adapted_from_id") == "p2"

    ctx = p2_accepted.get("collision_context")
    assert ctx is not None
    assert "p1" in ctx["conflicting_proposal_ids"]
    assert "compute" in ctx["reprompt_instruction"]
    assert "def compute(x): return x * 2" in ctx["accepted_patch_diffs"]
