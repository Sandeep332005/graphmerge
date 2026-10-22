import networkx as nx
from typing import List, Dict, Set, Tuple, Any


class ConflictGraphOptimizer:
    """Discrete Block Optimizer implementing Maximum Weight Independent Set (MWIS)

    and conflict graph arbitration for parallel AI agent code proposals.
    Directly grounded in arXiv:2610.30074.
    """

    def __init__(self):
        self.graph = nx.Graph()

    def build_conflict_graph(self, proposals: List[Dict[str, Any]]) -> nx.Graph:
        """Constructs an undirected conflict graph G = (V, E).

        Args:
            proposals: List of proposal dicts, each with:
                - 'id': str
                - 'files': Dict[str, Set[str]] (filename -> set of touched symbols)
                - 'weight': float (verified local objective improvement)

        Returns:
            NetworkX Graph where nodes are proposals and edges represent
            syntactic or semantic AST collisions.
        """
        self.graph.clear()
        for p in proposals:
            self.graph.add_node(p["id"], weight=float(p.get("weight", 1.0)), files=p.get("files", {}))

        p_list = list(self.graph.nodes(data=True))
        for i in range(len(p_list)):
            for j in range(i + 1, len(p_list)):
                id_i, data_i = p_list[i]
                id_j, data_j = p_list[j]

                has_collision = False
                conflicting_symbols = []

                for file_path, symbols_i in data_i["files"].items():
                    if file_path in data_j["files"]:
                        symbols_j = data_j["files"][file_path]
                        overlap = set(symbols_i).intersection(set(symbols_j))
                        if overlap:
                            has_collision = True
                            conflicting_symbols.extend(list(overlap))

                if has_collision:
                    self.graph.add_edge(
                        id_i,
                        id_j,
                        conflict_type="AST_SYMBOL_COLLISION",
                        symbols=conflicting_symbols,
                    )

        return self.graph

    def solve_mwis(self) -> Tuple[Set[str], Set[str]]:
        """Solves the Maximum Weight Independent Set (MWIS) problem.

        Uses exact clique search on the complement graph for |V| <= 20.

        Returns:
            Tuple of (accepted_patch_ids, deferred_patch_ids)
        """
        if self.graph.number_of_nodes() == 0:
            return set(), set()

        if self.graph.number_of_nodes() == 1:
            only_node = list(self.graph.nodes())[0]
            return {only_node}, set()

        # Complement graph clique search: Maximum Clique in complement G == Maximum Independent Set in G
        complement_g = nx.complement(self.graph)
        cliques = list(nx.find_cliques(complement_g))

        if not cliques:
            # Fallback if no cliques found
            return set(), set(self.graph.nodes())

        best_independent_set = max(
            cliques,
            key=lambda c: sum(self.graph.nodes[n].get("weight", 1.0) for n in c),
        )

        accepted = set(best_independent_set)
        rejected = set(self.graph.nodes()) - accepted
        return accepted, rejected

    def compute_fractional_bound(self) -> float:
        """Estimates the theoretical preservation bound 1 / chi_f(G)."""
        if self.graph.number_of_nodes() == 0:
            return 1.0
        # For small graphs, chromatic number serves as an upper bound on chi_f(G)
        try:
            d_max = max(dict(self.graph.degree()).values()) if self.graph.number_of_edges() > 0 else 0
            # Brooks' theorem upper bound: chi(G) <= Delta + 1
            chi_estimate = max(1, d_max + 1)
            return 1.0 / float(chi_estimate)
        except Exception:
            return 0.5
