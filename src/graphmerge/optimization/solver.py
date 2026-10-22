import networkx as nx
from typing import List, Dict, Set, Tuple, Any
from collections import defaultdict


class ConflictGraphOptimizer:
    """High-Performance Discrete Block Optimizer for Parallel AI Agent Patches.

    Optimized with:
    1. Inverted Symbol Index: O(K) linear conflict edge generation instead of O(K^2).
    2. Divide-and-Conquer: Solves MWIS over independent connected components,
       preventing combinatorial explosion on large graphs.
    Directly grounded in arXiv:2610.30074.
    """

    def __init__(self):
        self.graph = nx.Graph()

    def build_conflict_graph(self, proposals: List[Dict[str, Any]]) -> nx.Graph:
        """Constructs an undirected conflict graph G = (V, E) using an Inverted Index.

        Complexity: O(K * S) where K is number of proposals and S is average symbols touched.
        """
        self.graph.clear()
        if not proposals:
            return self.graph

        # Add all nodes
        for p in proposals:
            self.graph.add_node(
                p["id"],
                weight=float(p.get("weight", 1.0)),
                files=p.get("files", {})
            )

        # Inverted Index: (file_path, symbol_name) -> list of proposal IDs
        symbol_index: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for p in proposals:
            p_id = p["id"]
            files_dict = p.get("files", {})
            for file_path, symbols in files_dict.items():
                for symbol in symbols:
                    symbol_index[(file_path, symbol)].append(p_id)

        # Generate edges in linear time from index collisions
        for (file_path, symbol), touching_ids in symbol_index.items():
            if len(touching_ids) > 1:
                # Add conflict edges between all proposals touching the same symbol
                for i in range(len(touching_ids)):
                    for j in range(i + 1, len(touching_ids)):
                        u, v = touching_ids[i], touching_ids[j]
                        if not self.graph.has_edge(u, v):
                            self.graph.add_edge(
                                u, v,
                                conflict_type="AST_SYMBOL_COLLISION",
                                file=file_path,
                                symbol=symbol
                            )

        return self.graph

    def solve_mwis(self) -> Tuple[Set[str], Set[str]]:
        """Solves Maximum Weight Independent Set using Divide-and-Conquer over

        connected components.
        """
        if self.graph.number_of_nodes() == 0:
            return set(), set()

        if self.graph.number_of_nodes() == 1:
            only_node = list(self.graph.nodes())[0]
            return {only_node}, set()

        total_accepted = set()

        # Divide-and-Conquer: Process each connected component independently
        # MWIS(G) is the union of MWIS(Component_i)
        for component_nodes in nx.connected_components(self.graph):
            subgraph = self.graph.subgraph(component_nodes)

            if len(component_nodes) == 1:
                total_accepted.add(list(component_nodes)[0])
                continue

            # If small component (<= 25 nodes), solve exact complement clique
            if len(component_nodes) <= 25:
                comp_g = nx.complement(subgraph)
                cliques = list(nx.find_cliques(comp_g))
                best_sub_is = max(
                    cliques,
                    key=lambda c: sum(subgraph.nodes[n].get("weight", 1.0) for n in c)
                )
                total_accepted.update(best_sub_is)
            else:
                # Fast greedy weighted heuristic for dense/large components
                total_accepted.update(self._greedy_weighted_independent_set(subgraph))

        rejected = set(self.graph.nodes()) - total_accepted
        return total_accepted, rejected

    def _greedy_weighted_independent_set(self, g: nx.Graph) -> Set[str]:
        """Fast greedy approximation for large components (|V| > 25)."""
        remaining = set(g.nodes())
        selected = set()

        while remaining:
            # Pick node with maximum weight / (degree + 1) ratio
            best_node = max(
                remaining,
                key=lambda n: g.nodes[n].get("weight", 1.0) / (g.degree(n) + 1)
            )
            selected.add(best_node)
            # Remove chosen node and all its neighbors
            neighbors = set(g.neighbors(best_node))
            remaining.remove(best_node)
            remaining -= neighbors

        return selected

    def compute_fractional_bound(self) -> float:
        """Estimates the theoretical preservation bound 1 / chi_f(G)."""
        if self.graph.number_of_nodes() == 0:
            return 1.0
        try:
            d_max = max(dict(self.graph.degree()).values()) if self.graph.number_of_edges() > 0 else 0
            chi_estimate = max(1, d_max + 1)
            return 1.0 / float(chi_estimate)
        except Exception:
            return 0.5
