import json
import sys
from typing import Dict, Any, List, Optional
from graphmerge.optimization.solver import ConflictGraphOptimizer
from graphmerge.analysis.ast_parser import (
    extract_modified_lines,
    extract_symbol_analysis,
    extract_hunk_code,
    validate_diff_syntax,
)

# Dual compatibility: support MCP 2.x (MCPServer) and MCP 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    mcp = FastMCP("graphmerge-arbiter")
    HAS_MCP = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("graphmerge-arbiter")
        HAS_MCP = True
    except ImportError:
        HAS_MCP = False
        mcp = None


optimizer = ConflictGraphOptimizer()


def arbitrate_merge_proposals(proposals_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Core function to arbitrate multiple candidate agent proposals (pre-extracted symbols)."""
    g = optimizer.build_conflict_graph(proposals_data)
    accepted, rejected = optimizer.solve_mwis()
    bound = optimizer.compute_fractional_bound()
    diagnostics = optimizer.get_conflict_diagnostics()

    return {
        "status": "success",
        "accepted_proposals": list(accepted),
        "deferred_proposals": list(rejected),
        "total_nodes": g.number_of_nodes(),
        "total_conflict_edges": g.number_of_edges(),
        "conflict_diagnostics": diagnostics,
        "preservation_bound_guarantee": bound,
    }


def arbitrate_diff_patches_core(diff_patches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parses raw unified diffs with Tree-Sitter AST, checks syntax,

    and runs two-tier conflict arbitration.
    """
    proposals_payload = []
    syntax_rejected = []

    for item in diff_patches:
        p_id = item.get("id", "patch")
        diff_text = item.get("diff", item.get("diff_content", ""))
        weight = float(item.get("weight", 1.0))
        task_id = item.get("task_id", p_id)

        # Validate syntax
        if not validate_diff_syntax(diff_text):
            syntax_rejected.append({
                "id": p_id,
                "task_id": task_id,
                "reason": "Diff failed AST syntax validation",
            })
            continue

        # Extract modified lines and two-tier symbol analysis from hunk code
        lines_by_file = extract_modified_lines(diff_text)
        hunk_code = extract_hunk_code(diff_text)
        hunk_bytes = hunk_code.encode("utf-8", errors="ignore")
        hunk_line_count = len(hunk_code.splitlines())
        hunk_lines = list(range(1, max(2, hunk_line_count + 1)))
        analysis = extract_symbol_analysis(hunk_bytes, hunk_lines)

        symbol_analysis = {}
        if lines_by_file:
            for file_path in lines_by_file.keys():
                symbol_analysis[file_path] = analysis
        else:
            symbol_analysis["snippet.py"] = analysis

        proposals_payload.append({
            "id": p_id,
            "task_id": task_id,
            "weight": weight,
            "symbol_analysis": symbol_analysis,
            "diff_content": diff_text,
        })

    g = optimizer.build_conflict_graph(proposals_payload)
    accepted, rejected = optimizer.solve_mwis()
    bound = optimizer.compute_fractional_bound()
    diagnostics = optimizer.get_conflict_diagnostics()

    return {
        "status": "success",
        "accepted_patches": list(accepted),
        "deferred_patches": list(rejected),
        "syntax_rejected_patches": syntax_rejected,
        "total_patches_evaluated": len(diff_patches),
        "total_conflict_edges": g.number_of_edges(),
        "conflict_diagnostics": diagnostics,
        "preservation_bound": bound,
    }


def check_patch_collision_core(diff_a: str, diff_b: str, id_a: str = "patch_a", id_b: str = "patch_b") -> Dict[str, Any]:
    """Checks whether two diffs collide under Tier 1 (Syntactic) or Tier 2 (Def-Use) analysis."""
    res = arbitrate_diff_patches_core([
        {"id": id_a, "diff": diff_a, "weight": 1.0},
        {"id": id_b, "diff": diff_b, "weight": 1.0},
    ])
    has_conflict = res["total_conflict_edges"] > 0
    diagnostics = res.get("conflict_diagnostics", [])
    first_diag = diagnostics[0] if diagnostics else {}

    return {
        "has_conflict": has_conflict,
        "can_merge_concurrently": not has_conflict,
        "conflict_type": first_diag.get("conflict_type", "NONE") if has_conflict else "NONE",
        "tier": first_diag.get("tier", 0) if has_conflict else 0,
        "symbol": first_diag.get("symbol", "") if has_conflict else "",
        "details": first_diag,
    }


# ============================================================================
# MCP Tool Registrations (Available in Antigravity, Claude Code, Cursor, etc.)
# ============================================================================
if HAS_MCP and mcp:

    @mcp.tool()
    def arbitrate_diff_patches(diffs_json: str) -> str:
        """Takes a JSON array of diff patches (each with 'id', 'diff', and optional 'weight'),

        extracts AST symbols with Tree-Sitter, detects syntactic and def-use conflicts,
        and returns the certified conflict-free independent set I* with preservation guarantees.
        """
        try:
            data = json.loads(diffs_json)
            result = arbitrate_diff_patches_core(data)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def check_patch_collision(diff_a: str, diff_b: str, id_a: str = "patch_a", id_b: str = "patch_b") -> str:
        """Compares two candidate unified diffs and returns whether they can be merged simultaneously

        or collide under Tier 1 (Syntactic Definitions) or Tier 2 (Cross-File Def-Use Call Graphs).
        """
        try:
            result = check_patch_collision_core(diff_a, diff_b, id_a, id_b)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def solve_merge(proposals_json: str) -> str:
        """Takes a JSON string of proposals with pre-extracted symbol sets and weights,

        returning the certified Maximum Weight Independent Set I*.
        """
        try:
            data = json.loads(proposals_json)
            result = arbitrate_merge_proposals(data)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    def generate_reprompt_instruction(
        task_id: str,
        colliding_patch_ids: str,
        colliding_symbols: str,
        baseline_version: str = "s_1"
    ) -> str:
        """Generates an adaptive re-prompt instruction for an LLM worker agent whose patch was deferred

        due to conflict collisions, instructing it on how to regenerate its patch grounded in the updated baseline.
        """
        instruction = (
            f"Your prior proposed patch for task '{task_id}' was deferred by the GraphMerge coordinator "
            f"due to AST symbol collisions with patch(es) [{colliding_patch_ids}] on symbol(s) [{colliding_symbols}]. "
            f"The accepted patch has been atomically committed into baseline {baseline_version}. "
            f"Please regenerate your patch grounded in the updated symbols in {baseline_version}."
        )
        return json.dumps({
            "task_id": task_id,
            "target_baseline": baseline_version,
            "instruction": instruction
        }, indent=2)


def main():
    if HAS_MCP and mcp:
        sys.stderr.write("Starting GraphMerge MCP Server (stdio transport for Antigravity & Claude Code)...\n")
        sys.stderr.flush()
        mcp.run()
    else:
        sys.stderr.write("MCP library not available. Running fallback CLI demo:\n")
        demo = [
            {"id": "p1", "files": {"math.py": ["ratio"]}, "weight": 10.0},
            {"id": "p2", "files": {"math.py": ["ratio"]}, "weight": 8.0},
            {"id": "p3", "files": {"format.py": ["iso"]}, "weight": 12.0},
        ]
        res = arbitrate_merge_proposals(demo)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
