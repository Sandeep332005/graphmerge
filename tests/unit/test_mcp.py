import pytest
import json
from graphmerge.mcp_server import (
    arbitrate_merge_proposals,
    arbitrate_diff_patches_core,
    check_patch_collision_core,
    generate_reprompt_instruction,
)


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


def test_mcp_diff_arbitration_and_collision_checks():
    """Verifies MCP tools for diff arbitration and Tier 1 / Tier 2 collision checks."""
    diff_a = """diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -1,2 +1,3 @@
 def handle_request(req):
+    return req.data * 2
"""
    diff_b = """diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -1,2 +1,3 @@
 def handle_request(req):
+    return req.data * 3
"""
    diff_c = """diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -1,2 +1,3 @@
 def format_header(h):
+    return h.upper()
"""

    # 1. Test check_patch_collision
    col = check_patch_collision_core(diff_a, diff_b)
    assert col["has_conflict"] is True
    assert col["conflict_type"] == "TIER1_SYNTACTIC_COLLISION"
    assert col["symbol"] == "handle_request"

    no_col = check_patch_collision_core(diff_a, diff_c)
    assert no_col["has_conflict"] is False

    # 2. Test arbitrate_diff_patches_core
    res = arbitrate_diff_patches_core([
        {"id": "patch_1", "diff": diff_a, "weight": 10.0},
        {"id": "patch_2", "diff": diff_b, "weight": 6.0},
        {"id": "patch_3", "diff": diff_c, "weight": 14.0},
    ])
    assert set(res["accepted_patches"]) == {"patch_1", "patch_3"}
    assert res["deferred_patches"] == ["patch_2"]
    assert res["preservation_bound"] == 0.5

    # 3. Test generate_reprompt_instruction
    instr_raw = generate_reprompt_instruction("TASK-42", "patch_1", "handle_request", "s_1")
    instr = json.loads(instr_raw)
    assert instr["task_id"] == "TASK-42"
    assert "handle_request" in instr["instruction"]
    assert "s_1" in instr["target_baseline"]
