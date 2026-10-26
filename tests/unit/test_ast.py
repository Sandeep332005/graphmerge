import pytest
from graphmerge.analysis.ast_parser import extract_modified_lines, extract_symbols_from_source

def test_extract_modified_lines():
    sample_diff = """--- a/math_utils.py
+++ b/math_utils.py
@@ -10,3 +10,4 @@ def helper():
 def calculate_ratio(a, b):
+    if b == 0:
+        return 0.0
     return a / b
"""
    modified = extract_modified_lines(sample_diff)
    assert "math_utils.py" in modified
    # Only the two added lines count; the context lines at 10 and 13 do not.
    assert modified["math_utils.py"] == [11, 12]

def test_extract_symbols_from_source():
    source_code = b"""
import math

def calculate_ratio(a, b):
    if b == 0:
        return 0.0
    return a / b

class Formatter:
    def format_iso(self, ts):
        return str(ts)
"""
    # Line 5 is inside calculate_ratio
    symbols = extract_symbols_from_source(source_code, [5])
    assert "calculate_ratio" in symbols
    assert "Formatter" not in symbols
    assert "format_iso" not in symbols

    # Line 11 is inside format_iso
    symbols_2 = extract_symbols_from_source(source_code, [11])
    assert "format_iso" in symbols_2 or "Formatter" in symbols_2
