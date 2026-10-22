import json
from typing import Dict, Any, List
from graphmerge.optimization.solver import ConflictGraphOptimizer

# We support FastMCP if available, otherwise provide standard CLI interface
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("graphmerge-arbiter")
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    mcp = None


optimizer = ConflictGraphOptimizer()


def arbitrate_merge_proposals(proposals_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Core function to arbitrate multiple candidate agent diffs."""
    g = optimizer.build_conflict_graph(proposals_data)
    accepted, rejected = optimizer.solve_mwis()
    bound = optimizer.compute_fractional_bound()

    return {
        "accepted_proposals": list(accepted),
        "deferred_proposals": list(rejected),
        "total_nodes": g.number_of_nodes(),
        "total_conflict_edges": g.number_of_edges(),
        "preservation_bound_guarantee": bound,
    }


if HAS_MCP and mcp:
    @mcp.tool()
    def solve_merge(proposals_json: str) -> str:
        """Takes a JSON string of proposals and returns the certified Maximum Weight Independent Set."""
        data = json.loads(proposals_json)
        result = arbitrate_merge_proposals(data)
        return json.dumps(result, indent=2)


def main():
    if HAS_MCP and mcp:
        print("Starting GraphMerge FastMCP Server on stdio...")
        mcp.run()
    else:
        print("FastMCP library not installed. Running demo arbiter test:")
        demo = [
            {"id": "p1", "files": {"math.py": ["ratio"]}, "weight": 10.0},
            {"id": "p2", "files": {"math.py": ["ratio"]}, "weight": 8.0},
            {"id": "p3", "files": {"format.py": ["iso"]}, "weight": 12.0},
        ]
        res = arbitrate_merge_proposals(demo)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
