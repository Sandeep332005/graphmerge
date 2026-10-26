from graphmerge.analysis.ast_parser import extract_hunk_code, validate_diff_syntax


def test_no_newline_marker_is_dropped():
    diff = """diff --git a/demo.py b/demo.py
--- a/demo.py
+++ b/demo.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
\\ No newline at end of file
"""
    code = extract_hunk_code(diff)
    assert "No newline" not in code
    assert code.splitlines() == ["x = 1", "y = 2"]


def test_metadata_line_does_not_break_syntax_validation():
    diff = """diff --git a/demo.py b/demo.py
--- a/demo.py
+++ b/demo.py
@@ -1,1 +1,2 @@
+def ok():
+    return 1
\\ No newline at end of file
"""
    assert validate_diff_syntax(diff) is True
