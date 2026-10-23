import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from graphmerge.orchestration.supervisor import build_graphmerge_state_graph
from graphmerge.orchestration.state import GraphMergeState, AgentProposal
from graphmerge.optimization.solver import ConflictGraphOptimizer
from graphmerge.analysis.ast_parser import extract_symbol_analysis, validate_diff_syntax


def simulate_parallel_worker(task_id: str, file_name: str, symbol_name: str, weight: float) -> AgentProposal:
    """Simulates an autonomous AI worker agent running in a parallel thread:

    1. Analyzes target source code with AST parsing.
    2. Validates proposed diff syntax.
    3. Produces a certified proposal with empirical gain Delta f_i.
    """
    diff_content = f"""diff --git a/{file_name} b/{file_name}
--- a/{file_name}
+++ b/{file_name}
@@ -1,2 +1,3 @@
 def {symbol_name}():
+    # Parallel task {task_id} enhancement
     return 42
"""
    # Verify diff syntax inside worker thread
    assert validate_diff_syntax(diff_content) is True

    # Simulate slight worker compute latency
    time.sleep(0.01)

    return {
        "id": f"prop_{task_id}",
        "agent_id": f"agent_{task_id}",
        "task_id": task_id,
        "diff_content": diff_content,
        "target_files": [file_name],
        "touched_symbols": {file_name: {symbol_name}},
        "symbol_analysis": {
            file_name: {
                "definitions": {symbol_name},
                "calls": set(),
                "imports": set(),
            }
        },
        "verified_local_gain": weight,
    }


def test_concurrent_worker_dispatch_and_arbitration():
    """Verifies that multiple worker agents can execute tasks in parallel threads,

    submit proposals concurrently, and have their proposals arbitrated with 0 race conditions.
    """
    tasks = [
        # Pair 1: Colliding on pipeline.py:transform
        ("T1", "pipeline.py", "transform", 14.0),
        ("T2", "pipeline.py", "transform", 9.0),
        # Pair 2: Colliding on auth.py:authenticate
        ("T3", "auth.py", "authenticate", 11.0),
        ("T4", "auth.py", "authenticate", 7.0),
        # Pair 3: Independent parallel tasks
        ("T5", "logger.py", "setup_log", 15.0),
        ("T6", "cache.py", "get_cache", 13.0),
        ("T7", "metrics.py", "record_stat", 8.0),
        ("T8", "health.py", "ping", 6.0),
    ]

    proposals = []
    t0 = time.perf_counter()

    # Execute 8 workers concurrently in parallel threads
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(simulate_parallel_worker, t_id, f_name, s_name, w)
            for (t_id, f_name, s_name, w) in tasks
        ]
        for f in as_completed(futures):
            proposals.append(f.result())

    wall_time = (time.perf_counter() - t0) * 1000

    assert len(proposals) == 8
    # With 8 concurrent threads sleeping 10ms each, wall time should be well under 8 * 10 = 80ms
    assert wall_time < 60.0, f"Parallel execution was unexpectedly sequential: {wall_time:.2f}ms"

    # Coordinator arbitrates the concurrently submitted proposals
    optimizer = ConflictGraphOptimizer()
    g = optimizer.build_conflict_graph([
        {"id": p["id"], "symbol_analysis": p["symbol_analysis"], "weight": p["verified_local_gain"]}
        for p in proposals
    ])

    assert g.number_of_nodes() == 8
    # Should identify 2 conflict edges: (prop_T1, prop_T2) and (prop_T3, prop_T4)
    assert g.number_of_edges() == 2

    accepted, rejected = optimizer.solve_mwis()

    # Higher weight in colliding pairs must be accepted
    assert "prop_T1" in accepted  # 14.0 > 9.0
    assert "prop_T2" in rejected
    assert "prop_T3" in accepted  # 11.0 > 7.0
    assert "prop_T4" in rejected

    # All independent parallel tasks must be accepted
    for indep_id in ["prop_T5", "prop_T6", "prop_T7", "prop_T8"]:
        assert indep_id in accepted

    # Total accepted: 6, total rejected: 2
    assert len(accepted) == 6
    assert len(rejected) == 2

    # Independence Invariant: Zero edges between any pair in accepted set
    for u in accepted:
        for v in accepted:
            if u != v:
                assert not g.has_edge(u, v)


def test_end_to_end_parallel_backlog_convergence():
    """End-to-end integration test of parallel task convergence across 2 cycles:

    Cycle 1: 6 parallel tasks dispatched -> 4 accepted into s_1, 2 deferred.
    Cycle 2: 2 deferred workers adaptively re-prompted against s_1 -> both accepted into s_2.
    Result: 100% convergence across all parallel tasks with zero unmerged leftovers.
    """
    app = build_graphmerge_state_graph()

    parallel_tasks = [
        {"id": "TASK-1", "file": "data.py", "func": "clean_data", "weight": 10.0},
        {"id": "TASK-2", "file": "data.py", "func": "clean_data", "weight": 8.0},  # Collides with TASK-1
        {"id": "TASK-3", "file": "net.py", "func": "connect", "weight": 12.0},
        {"id": "TASK-4", "file": "net.py", "func": "connect", "weight": 7.0},    # Collides with TASK-3
        {"id": "TASK-5", "file": "render.py", "func": "draw", "weight": 15.0},    # Independent
        {"id": "TASK-6", "file": "export.py", "func": "to_csv", "weight": 11.0},   # Independent
    ]

    # Generate proposals concurrently
    proposals = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(simulate_parallel_worker, t["id"], t["file"], t["func"], t["weight"])
            for t in parallel_tasks
        ]
        for f in as_completed(futures):
            proposals.append(f.result())

    initial_state: GraphMergeState = {
        "workspace_path": "/tmp/parallel_workspace",
        "iteration": 0,
        "max_iterations": 3,
        "active_backlog": parallel_tasks,
        "proposals": proposals,
        "accepted_patches": [],
        "staged_patches": [],
        "is_converged": False,
        "summary_report": None,
    }

    final_state = app.invoke(initial_state)

    # Convergence reached in exactly 2 cycles
    assert final_state["is_converged"] is True
    assert final_state["iteration"] == 2

    accepted_ids = {p["id"] for p in final_state["accepted_patches"]}
    staged_ids = {p["id"] for p in final_state["staged_patches"]}

    # All 6 parallel tasks successfully committed to baseline s_2
    assert len(accepted_ids) == 6
    assert staged_ids == set()

    # Verify that the deferred proposals (TASK-2 and TASK-4) have collision contexts recorded
    p_task2 = next(p for p in final_state["accepted_patches"] if p["task_id"] == "TASK-2")
    assert p_task2.get("collision_context") is not None
    assert "prop_TASK-1" in p_task2["collision_context"]["conflicting_proposal_ids"]
