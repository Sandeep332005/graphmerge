import pytest
from graphmerge.analysis.ast_parser import _AST_CACHE, extract_symbol_analysis

def test_ast_cache_eviction():
    # Insert more than 256 unique entries and verify size <= 256
    initial_len = len(_AST_CACHE)
    for i in range(300):
        dummy_code = f"def func_{i}():\n    return {i}\n".encode("utf-8")
        extract_symbol_analysis(dummy_code, [1])

    assert len(_AST_CACHE) <= 256

def test_ast_range_intersection():
    code = """
def alpha():
    x = 1
    return x

def beta():
    y = 2
    return y
""".encode("utf-8")

    # Only lines 2-4 modified (inside alpha)
    analysis_alpha = extract_symbol_analysis(code, [3])
    assert "alpha" in analysis_alpha["definitions"]
    assert "beta" not in analysis_alpha["definitions"]

    # Only lines 6-8 modified (inside beta)
    analysis_beta = extract_symbol_analysis(code, [7])
    assert "beta" in analysis_beta["definitions"]
    assert "alpha" not in analysis_beta["definitions"]
