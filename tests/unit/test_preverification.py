import pytest
from graphmerge.orchestration.supervisor import worker_preverification_node
from graphmerge.orchestration.state import GraphMergeState


def test_worker_preverification_filtering():
    """Verifies that the pre-verification node:

    1. Filters out patches with non-positive local gains (Delta f <= 0).
    2. Filters out patches with AST syntax errors.
    3. Keeps verified valid patches.
    """
    state: GraphMergeState = {
        "iteration": 0,
        "proposals": [
            {
                "id": "p_valid",
                "diff_content": "def hello():\n    return 'world'",
                "verified_local_gain": 5.0,
            },
            {
                "id": "p_syntax_error",
                "diff_content": "def broken(\n",
                "verified_local_gain": 8.0,
            },
            {
                "id": "p_negative_gain",
                "diff_content": "def sub(a, b): return a - b",
                "verified_local_gain": -2.0,
            },
            {
                "id": "p_zero_gain",
                "diff_content": "def pass_through(x): return x",
                "verified_local_gain": 0.0,
            },
        ],
        "rejected_unverified_patches": [],
    }

    result = worker_preverification_node(state)
    valid_ids = [p["id"] for p in result["proposals"]]
    rejected_ids = [p["id"] for p in result["rejected_unverified_patches"]]

    assert valid_ids == ["p_valid"]
    assert "p_syntax_error" in rejected_ids
    assert "p_negative_gain" in rejected_ids
    assert "p_zero_gain" in rejected_ids

    # Check verification records
    syntax_rej = next(p for p in result["rejected_unverified_patches"] if p["id"] == "p_syntax_error")
    assert syntax_rej["verification"]["status"] == "FAILED"
    assert syntax_rej["verification"]["syntax_valid"] is False

    valid_rec = result["proposals"][0]
    assert valid_rec["verification"]["status"] == "PASSED"
    assert valid_rec["verification"]["empirical_gain"] == 5.0
