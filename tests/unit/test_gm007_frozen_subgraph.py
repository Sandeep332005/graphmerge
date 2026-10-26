from graphmerge.optimization.solver import ConflictGraphOptimizer


def test_solve_mwis_does_not_mutate_frozen_subgraph():
    """Complementing a subgraph view raises NetworkXError unless it is copied."""
    proposals = [
        {"id": "a", "files": {"x.py": {"shared"}}, "weight": 5.0},
        {"id": "b", "files": {"x.py": {"shared"}}, "weight": 3.0},
        {"id": "c", "files": {"y.py": {"other"}}, "weight": 1.0},
    ]
    optimizer = ConflictGraphOptimizer()
    optimizer.build_conflict_graph(proposals)

    accepted, rejected = optimizer.solve_mwis()

    # Heavier of the conflicting pair wins; the disjoint node is always kept.
    assert accepted == {"a", "c"}
    assert rejected == {"b"}
    # The source graph must still be intact after the solve.
    assert optimizer.graph.number_of_nodes() == 3
    assert optimizer.graph.has_edge("a", "b")
