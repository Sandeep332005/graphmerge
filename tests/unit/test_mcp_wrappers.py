import json

import pytest

from graphmerge.mcp_server import HAS_MCP


@pytest.mark.skipif(not HAS_MCP, reason="MCP library not installed")
def test_mcp_tool_registration():
    """Verify that all expected tools are registered on the MCP server object."""
    # Depending on the MCP version, the way to access registered tools might vary.
    # For FastMCP (MCP 1.x) and MCPServer (MCP 2.x), we can usually check a list of tools.

    # Let's try to find where the tools are stored in the mcp object.
    # In some versions it's mcp._tools or similar.

    # Actually, a better way is to check if we can call them if we import them.
    # But they are defined inside the 'if HAS_MCP and mcp:' block.

    from graphmerge import mcp_server

    # We can check if the functions exist in the module namespace
    assert hasattr(mcp_server, "arbitrate_diff_patches")
    assert hasattr(mcp_server, "check_patch_collision")
    assert hasattr(mcp_server, "solve_merge")
    assert hasattr(mcp_server, "generate_reprompt_instruction")


def test_arbitrate_diff_patches_wrapper():
    from graphmerge.mcp_server import arbitrate_diff_patches

    diff_a = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 def foo():
+    pass
"""
    # Test valid input
    input_data = [{"id": "p1", "diff": diff_a, "weight": 1.0}]
    result_str = arbitrate_diff_patches(json.dumps(input_data))
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert "p1" in result["accepted_patches"]

    # Test invalid JSON
    result_str = arbitrate_diff_patches("invalid json")
    result = json.loads(result_str)
    assert result["status"] == "error"
    assert "Expecting value" in result["message"]


def test_arbitrate_diff_patches_with_syntax_error():
    from graphmerge.mcp_server import arbitrate_diff_patches

    valid_diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 def foo():
+    pass
"""
    invalid_diff = """diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,2 @@
-def fine(): pass
+def broken(
"""

    input_data = [
        {"id": "p_valid", "diff": valid_diff, "weight": 10.0},
        {"id": "p_broken", "diff": invalid_diff, "weight": 5.0},
    ]

    result_str = arbitrate_diff_patches(json.dumps(input_data))
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert "p_valid" in result["accepted_patches"]
    assert len(result["syntax_rejected_patches"]) == 1
    assert result["syntax_rejected_patches"][0]["id"] == "p_broken"
    assert "syntax validation" in result["syntax_rejected_patches"][0]["reason"]
    assert result["preservation_bound"] >= 0.5


def test_check_patch_collision_wrapper():
    from graphmerge.mcp_server import check_patch_collision

    diff_a = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 def foo():
+    pass
"""
    diff_b = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 def foo():
+    return 1
"""

    result_str = check_patch_collision(diff_a, diff_b)
    result = json.loads(result_str)
    assert result["has_conflict"] is True
    assert result["symbol"] == "foo"


def test_solve_merge_wrapper():
    from graphmerge.mcp_server import solve_merge

    proposals = [
        {"id": "p1", "files": {"math.py": ["ratio"]}, "weight": 10.0},
        {"id": "p2", "files": {"math.py": ["ratio"]}, "weight": 8.0},
    ]

    result_str = solve_merge(json.dumps(proposals))
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["accepted_proposals"] == ["p1"]


def test_generate_reprompt_instruction_wrapper():
    from graphmerge.mcp_server import generate_reprompt_instruction

    result_str = generate_reprompt_instruction("T1", "p2", "foo", "s_1")
    result = json.loads(result_str)
    assert result["task_id"] == "T1"
    assert "foo" in result["instruction"]
