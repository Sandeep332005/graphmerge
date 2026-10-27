from graphmerge.optimization.solver import ConflictGraphOptimizer


def test_mwis_conflict_arbitration():
    """Verify that the optimizer correctly detects collisions and selects

    the independent set with maximum objective gain.
    """
    optimizer = ConflictGraphOptimizer()

    proposals = [
        {"id": "patch_1", "files": {"math_utils.py": {"calculate_ratio"}}, "weight": 10.0},
        {
            "id": "patch_2",
            "files": {"math_utils.py": {"calculate_ratio"}},
            "weight": 8.0,
        },  # Collides with patch_1
        {
            "id": "patch_3",
            "files": {"formatters.py": {"format_iso"}},
            "weight": 12.0,
        },  # Independent
    ]

    optimizer.build_conflict_graph(proposals)
    accepted, rejected = optimizer.solve_mwis()

    # patch_1 (10) + patch_3 (12) = 22 > patch_2 (8) + patch_3 (12) = 20
    assert accepted == {"patch_1", "patch_3"}
    assert rejected == {"patch_2"}


def test_empty_proposals():
    optimizer = ConflictGraphOptimizer()
    optimizer.build_conflict_graph([])
    accepted, rejected = optimizer.solve_mwis()
    assert accepted == set()
    assert rejected == set()


def test_single_proposal():
    optimizer = ConflictGraphOptimizer()
    optimizer.build_conflict_graph([{"id": "single", "files": {"a.py": {"func"}}, "weight": 5.0}])
    accepted, rejected = optimizer.solve_mwis()
    assert accepted == {"single"}
    assert rejected == set()
