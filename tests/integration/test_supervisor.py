from graphmerge.orchestration.state import GraphMergeState
from graphmerge.orchestration.supervisor import build_graphmerge_state_graph


def test_full_langgraph_pipeline_execution():
    """End-to-End integration test:

    Verifies that the compiled LangGraph StateGraph runs through fan-out,
    calls the discrete optimizer, selects the certified independent set,
    and cleanly marks convergence.
    """
    app = build_graphmerge_state_graph()

    initial_state: GraphMergeState = {
        "workspace_path": "/tmp/test_workspace",
        "iteration": 0,
        "max_iterations": 3,
        "active_backlog": [
            {"id": "T1", "desc": "Fix division by zero in calculate_ratio"},
            {"id": "T2", "desc": "Add type validation to calculate_ratio"},
            {"id": "T3", "desc": "Fix ISO formatting in formatters.py"},
        ],
        "proposals": [
            {
                "id": "p1",
                "agent_id": "agent_1",
                "task_id": "T1",
                "diff_content": "diff --git a/math.py",
                "target_files": ["math.py"],
                "touched_symbols": {"math.py": {"calculate_ratio"}},
                "verified_local_gain": 10.0,
            },
            {
                "id": "p2",
                "agent_id": "agent_2",
                "task_id": "T2",
                "diff_content": "diff --git a/math.py",
                "target_files": ["math.py"],
                "touched_symbols": {"math.py": {"calculate_ratio"}},  # Collides with p1
                "verified_local_gain": 8.0,
            },
            {
                "id": "p3",
                "agent_id": "agent_3",
                "task_id": "T3",
                "diff_content": "diff --git a/fmt.py",
                "target_files": ["fmt.py"],
                "touched_symbols": {"fmt.py": {"format_iso"}},  # Independent
                "verified_local_gain": 12.0,
            },
        ],
        "accepted_patches": [],
        "staged_patches": [],
        "is_converged": False,
        "summary_report": None,
    }

    # Execute the LangGraph workflow to convergence
    final_output = app.invoke(initial_state)

    accepted_ids = {p["id"] for p in final_output["accepted_patches"]}
    staged_ids = {p["id"] for p in final_output["staged_patches"]}

    # The pipeline should run across 2 iterations:
    # Cycle 1: Accepts independent set {p1, p3}, stages {p2}
    # Cycle 2: Rebases and integrates {p2} onto the updated baseline
    # Result: All 3 tasks successfully resolved, 0 remaining staged, converged!
    assert accepted_ids == {
        "p1",
        "p2",
        "p3",
    }, f"Expected all 3 accepted across 2 cycles, got {accepted_ids}"
    assert staged_ids == set(), f"Expected empty staged queue upon convergence, got {staged_ids}"
    assert final_output["is_converged"] is True
    assert (
        final_output["iteration"] == 2
    ), f"Expected convergence in 2 cycles, got {final_output['iteration']}"
