from graphmerge.optimization.solver import ConflictGraphOptimizer


def test_both_tiers_are_preserved_on_one_edge():
    # p1 defines `helper` in util.py; p2 both redefines it in util.py (Tier 1)
    # and calls it from app.py (Tier 2). Both causes must survive on the edge.
    proposals = [
        {
            "id": "p1",
            "weight": 1.0,
            "symbol_analysis": {
                "util.py": {"definitions": {"helper"}, "calls": set(), "imports": set()},
            },
        },
        {
            "id": "p2",
            "weight": 1.0,
            "symbol_analysis": {
                "util.py": {"definitions": {"helper"}, "calls": set(), "imports": set()},
                "app.py": {"definitions": set(), "calls": {"helper"}, "imports": set()},
            },
        },
    ]
    optimizer = ConflictGraphOptimizer()
    optimizer.build_conflict_graph(proposals)

    assert optimizer.graph.number_of_edges() == 1
    data = optimizer.graph.edges["p1", "p2"]
    assert data["conflict_type"] == "TIER1_AND_TIER2_COLLISION"
    assert data["tier"] == "1+2"
    assert "helper" in data["symbol"] if isinstance(data["symbol"], list) else data["symbol"] == "helper"

    diagnostics = optimizer.get_conflict_diagnostics()
    assert diagnostics[0]["conflict_type"] == "TIER1_AND_TIER2_COLLISION"
