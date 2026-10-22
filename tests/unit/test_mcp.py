import pytest
import json
from graphmerge.mcp_server import arbitrate_merge_proposals


def test_mcp_arbiter_logic():
    proposals = [
        {"id": "p1", "files": {"math.py": ["ratio"]}, "weight": 10.0},
        {"id": "p2", "files": {"math.py": ["ratio"]}, "weight": 8.0},
        {"id": "p3", "files": {"format.py": ["iso"]}, "weight": 12.0},
    ]

    result = arbitrate_merge_proposals(proposals)

    assert set(result["accepted_proposals"]) == {"p1", "p3"}
    assert result["deferred_proposals"] == ["p2"]
    assert result["total_nodes"] == 3
    assert result["total_conflict_edges"] == 1
    assert result["preservation_bound_guarantee"] == 0.5
