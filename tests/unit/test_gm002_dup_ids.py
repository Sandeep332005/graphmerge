
import pytest
from graphmerge.optimization.solver import ConflictGraphOptimizer

def test_duplicate_id_raises():
    optimizer = ConflictGraphOptimizer()
    proposals = [
        {"id": "p1", "weight": 1.0},
        {"id": "p1", "weight": 1.0}
    ]
    with pytest.raises(ValueError, match="Duplicate proposal id 'p1'"):
        optimizer.build_conflict_graph(proposals)

def test_unique_ids_build_correctly():
    optimizer = ConflictGraphOptimizer()
    proposals = [
        {"id": "p1", "weight": 1.0},
        {"id": "p2", "weight": 1.0}
    ]
    g = optimizer.build_conflict_graph(proposals)
    assert g.number_of_nodes() == 2
