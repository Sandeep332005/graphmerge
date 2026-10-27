from graphmerge.analysis.ast_parser import (
    extract_symbol_analysis,
    validate_diff_syntax,
)
from graphmerge.optimization.solver import ConflictGraphOptimizer


def test_extract_symbol_analysis_two_tier():
    """Verifies that extract_symbol_analysis extracts definitions and call sites."""
    code = b"""
import os
from math_utils import calculate_tax

def process_order(order):
    total = calculate_tax(order.total, 0.05)
    return total
"""
    # Lines 5-7 are the function body and call
    analysis = extract_symbol_analysis(code, [5, 6, 7])
    assert "process_order" in analysis["definitions"]
    assert "calculate_tax" in analysis["calls"]


def test_tier2_def_use_conflict_resolution():
    """Verifies Tier 2 Def-Use Call Graph Conflict Detection:

    Proposal A modifies definition of `calculate_tax` in `math.py`.
    Proposal B modifies `billing.py` and calls `calculate_tax`.
    The optimizer must detect the cross-file semantic collision and block concurrent apply.
    """
    optimizer = ConflictGraphOptimizer()

    proposals = [
        {
            "id": "p_def",
            "weight": 10.0,
            "symbol_analysis": {
                "math.py": {
                    "definitions": {"calculate_tax"},
                    "calls": set(),
                    "imports": set(),
                }
            },
        },
        {
            "id": "p_call",
            "weight": 7.0,
            "symbol_analysis": {
                "billing.py": {
                    "definitions": {"invoice"},
                    "calls": {"calculate_tax"},
                    "imports": set(),
                }
            },
        },
        {
            "id": "p_indep",
            "weight": 15.0,
            "symbol_analysis": {
                "auth.py": {
                    "definitions": {"login"},
                    "calls": set(),
                    "imports": set(),
                }
            },
        },
    ]

    g = optimizer.build_conflict_graph(proposals)

    # Must create a Tier 2 collision edge between p_def and p_call
    assert g.has_edge("p_def", "p_call")
    edge_data = g.edges["p_def", "p_call"]
    assert edge_data["conflict_type"] == "TIER2_DEF_USE_COLLISION"
    assert edge_data["tier"] == 2
    assert edge_data["symbol"] == "calculate_tax"

    # p_indep must not be connected
    assert not g.has_edge("p_indep", "p_def")
    assert not g.has_edge("p_indep", "p_call")

    accepted, rejected = optimizer.solve_mwis()
    # p_indep (15.0) + p_def (10.0) = 25.0 > p_indep (15.0) + p_call (7.0) = 22.0
    assert accepted == {"p_indep", "p_def"}
    assert rejected == {"p_call"}


def test_validate_diff_syntax():
    """Verifies diff syntax validation on clean, indented, and malformed diffs."""
    valid_diff = """diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,3 @@
-def add(a, b): return 0
+def add(a, b):
+    return a + b
"""
    assert validate_diff_syntax(valid_diff) is True

    broken_diff = """diff --git a/calc.py b/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
+def broken(
"""
    assert validate_diff_syntax(broken_diff) is False
