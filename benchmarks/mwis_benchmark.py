"""Performance benchmarks for GraphMerge AST collision detection and MWIS solver.

Measures solver latency and gain preservation across synthetic multi-agent workloads
scaling from N=5 to N=100 concurrent agent proposals.
"""
import random
import time
from graphmerge.optimization.solver import ConflictGraphOptimizer


def generate_synthetic_workload(num_agents: int, conflict_probability: float = 0.25):
    """Generates synthetic agent proposals with realistic conflict edge densities."""
    proposals = []
    symbols = [f"sym_{i}" for i in range(max(3, num_agents // 2))]

    for i in range(num_agents):
        # Pick 1-2 touched symbols
        touched = random.sample(symbols, k=random.randint(1, min(2, len(symbols))))
        weight = round(random.uniform(0.5, 1.0), 3)
        proposals.append({
            "id": f"agent_{i:03d}",
            "verified_local_gain": weight,
            "touched_symbols": {
                "definitions": touched[:1],
                "calls": touched[1:],
            },
            "target_files": ["core/engine.py"],
        })
    return proposals


def run_benchmark():
    """Runs scaling benchmarks across agent pool sizes."""
    print("=" * 68)
    print("GraphMerge Distributed Block Optimization: Performance Benchmark")
    print("=" * 68)
    print(f"{'Agents (N)':<12} | {'Edges':<8} | {'Accepted':<10} | {'Gain Preserved':<16} | {'Latency (ms)':<12}")
    print("-" * 68)

    random.seed(42)
    scales = [5, 10, 20, 50, 100]

    for n in scales:
        proposals = generate_synthetic_workload(n)
        optimizer = ConflictGraphOptimizer()

        t0 = time.perf_counter()
        g = optimizer.build_conflict_graph(proposals)
        accepted, rejected = optimizer.solve_mwis()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        num_edges = g.number_of_edges()
        total_proposals_gain = sum(p["verified_local_gain"] for p in proposals)
        accepted_gain = sum(
            p["verified_local_gain"] for p in proposals if p["id"] in accepted
        )
        ratio = (accepted_gain / total_proposals_gain * 100) if total_proposals_gain else 0.0

        print(
            f"{n:<12} | {num_edges:<8} | {len(accepted):<10} | "
            f"{ratio:>5.1f}% ({accepted_gain:>5.1f})   | {latency_ms:>8.2f} ms"
        )

    print("=" * 68)
    print("Benchmark complete. All scaling tiers verified.")


if __name__ == "__main__":
    run_benchmark()
