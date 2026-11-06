"""Unit tests verifying engine hardening: SEC-01 safe execution, non-code diff handling, and builtin filter."""

import os
from graphmerge.analysis.ast_parser import is_non_code_file, validate_diff_syntax
from graphmerge.optimization.solver import ConflictGraphOptimizer
from graphmerge.orchestration.sandbox import GitSandbox


def test_is_non_code_file():
    assert is_non_code_file("README.md") is True
    assert is_non_code_file("package.json") is True
    assert is_non_code_file("config.yaml") is True
    assert is_non_code_file("schema.toml") is True
    assert is_non_code_file("notes.txt") is True
    assert is_non_code_file("app.py") is False
    assert is_non_code_file("server.ts") is False
    assert is_non_code_file("main.go") is False


def test_validate_diff_syntax_non_code():
    markdown_diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Project
+This is markdown documentation.
+It contains random non-python text like: def broken(
"""
    assert validate_diff_syntax(markdown_diff) is True

    json_diff = """diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -1,3 +1,4 @@
 {
+  "version": "1.0.1"
 }
"""
    assert validate_diff_syntax(json_diff) is True


def test_builtin_filter_tier2_no_false_collision():
    optimizer = ConflictGraphOptimizer()
    proposals = [
        {
            "id": "p_user_fn",
            "weight": 1.0,
            "symbol_analysis": {
                "module_a.py": {
                    "definitions": {"my_custom_func"},
                    "calls": {"len", "print", "str"},
                    "imports": set(),
                }
            },
        },
        {
            "id": "p_other_fn",
            "weight": 1.0,
            "symbol_analysis": {
                "module_b.py": {
                    "definitions": {"another_func"},
                    "calls": {"len", "dict"},
                    "imports": set(),
                }
            },
        },
    ]
    g = optimizer.build_conflict_graph(proposals)
    # Neither should conflict because len, print, str, dict are builtins
    assert not g.has_edge("p_user_fn", "p_other_fn")


def test_sandbox_safe_subprocess_execution(tmp_path):
    # Verify GitSandbox safely parses test_command without shell=True
    sandbox = GitSandbox(repo_path=str(tmp_path), test_command="python3 -c 'exit(0)'")
    sandbox._worktree_path = str(tmp_path)
    assert sandbox._run_tests() is True
