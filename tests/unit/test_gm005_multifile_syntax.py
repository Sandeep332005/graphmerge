
import pytest
from graphmerge.analysis.ast_parser import validate_diff_syntax

def test_multifile_diff_syntax_independence():
    # File A adds class header, File B adds indented return
    # Concatenated they are valid, but per-file they are invalid.
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,1 @@
+class MyClass:
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
+    return 42
"""
    # This should be invalid because 'class MyClass:' is incomplete without body,
    # and '    return 42' is an indent error/outside function.
    assert validate_diff_syntax(diff) is False

def test_valid_multifile_diff():
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
+def foo():
+    pass
diff --git b/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
+x = 1
"""
    assert validate_diff_syntax(diff) is True
