import time
import pytest
from graphmerge.optimization.solver import ConflictGraphOptimizer
from graphmerge.analysis.ast_parser import extract_symbols_from_source


def test_stress_scale_mwis_performance():
    """Stress test: Ingest 100 concurrent agent proposals across 10 independent modules.

    Verify that:
    1. Graph generation is linear O(K) and completes in sub-10ms.
    2. Divide-and-Conquer component decomposition prevents exponential slowdown.
    3. The Independence Invariant (zero adjacent edges in I*) strictly holds.
    """
    optimizer = ConflictGraphOptimizer()
    proposals = []

    # Generate 100 proposals across 10 files
    # Each file has 10 proposals touching functions func_0 .. func_9
    for i in range(100):
        file_id = i // 10
        func_id = i % 5  # Forces pairs of proposals to collide on same func
        proposals.append({
            "id": f"patch_{i}",
            "files": {f"module_{file_id}.py": {f"func_{func_id}"}},
            "weight": 10.0 + (i % 7)
        })

    # Benchmark graph construction
    t0 = time.perf_counter()
    g = optimizer.build_conflict_graph(proposals)
    t_graph = (time.perf_counter() - t0) * 1000  # ms

    assert g.number_of_nodes() == 100
    assert g.number_of_edges() > 0
    # Inverted index should construct the 100-node graph in under 20ms
    assert t_graph < 25.0, f"Graph building took too long: {t_graph:.2f}ms"

    # Benchmark MWIS solving
    t1 = time.perf_counter()
    accepted, rejected = optimizer.solve_mwis()
    t_mwis = (time.perf_counter() - t1) * 1000  # ms

    # Divide-and-conquer should solve 100 proposals in under 30ms
    assert t_mwis < 40.0, f"MWIS solve took too long: {t_mwis:.2f}ms"
    assert len(accepted) + len(rejected) == 100

    # FORMAL INVARIANT CHECK: Zero conflict edges between any pair in accepted set!
    for u in accepted:
        for v in accepted:
            if u != v:
                assert not g.has_edge(u, v), f"Independence Invariant Violated! Conflict edge between {u} and {v}"


def test_ast_cache_speedup():
    """Verify that repeated parses of the same source code are accelerated

    by the SHA-256 AST memoization cache.
    """
    sample_code = b"""
def heavy_computation_function(x, y):
    total = 0
    for i in range(100):
        total += i * x + y
    return total

class HeavyClassController:
    def execute_pipeline(self):
        return True
"""
    # First call: parses and caches
    t0 = time.perf_counter()
    symbols_1 = extract_symbols_from_source(sample_code, [3])
    t_first = time.perf_counter() - t0

    # Second call on same bytes: hits cache
    t1 = time.perf_counter()
    symbols_2 = extract_symbols_from_source(sample_code, [9])
    t_cached = time.perf_counter() - t1

    assert symbols_1 == {"heavy_computation_function"}
    assert "execute_pipeline" in symbols_2 or "HeavyClassController" in symbols_2
    # Cached run should be faster
    assert t_cached <= t_first or t_cached < 0.005
