from graphmerge.analysis.ast_parser import extract_modified_lines


def test_context_lines_are_not_modified():
    diff = """--- a/math_utils.py
+++ b/math_utils.py
@@ -10,3 +10,4 @@ def helper():
 def calculate_ratio(a, b):
+    if b == 0:
+        return 0.0
     return a / b
"""
    modified = extract_modified_lines(diff)

    # The hunk starts at line 10; the two added lines land on 11 and 12.
    # Line 10 and the trailing context line exist in the new file but were
    # not changed, so they must not be reported as modifications.
    assert modified["math_utils.py"] == [11, 12]


def test_removed_lines_do_not_shift_added_lines():
    diff = """--- a/demo.py
+++ b/demo.py
@@ -5,4 +5,4 @@
 kept_before = 1
-old_value = 2
+new_value = 2
 kept_after = 3
"""
    modified = extract_modified_lines(diff)
    # new file: 5 kept_before, 6 new_value, 7 kept_after
    assert modified["demo.py"] == [6]
