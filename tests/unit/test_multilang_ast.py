from graphmerge.analysis.ast_parser import (
    detect_language,
    extract_hunks_per_file,
    extract_symbol_analysis,
    validate_diff_syntax,
)


def test_detect_language():
    assert detect_language("app.py") == "python"
    assert detect_language("index.js") == "javascript"
    assert detect_language("component.tsx") == "tsx"
    assert detect_language("main.ts") == "typescript"
    assert detect_language("server.go") == "go"
    assert detect_language("lib.rs") == "rust"
    assert detect_language("App.java") == "java"
    assert detect_language("unknown.xyz") == "python"


def test_javascript_symbol_extraction():
    code = b"""
function processOrder(order) {
    const total = calculateTax(order.total, 0.05);
    return total;
}

class OrderManager {
    constructor() {}
    submit() { return true; }
}
"""
    analysis = extract_symbol_analysis(code, [2, 3, 4], language="javascript")
    assert "processOrder" in analysis["definitions"]
    assert "calculateTax" in analysis["calls"]


def test_typescript_symbol_extraction():
    code = b"""
interface UserProfile {
    name: string;
    email: string;
}

function getUser(id: number): UserProfile {
    return fetchUser(id);
}

enum Role {
    Admin,
    User,
}
"""
    analysis = extract_symbol_analysis(code, [2, 7, 8, 11], language="typescript")
    assert "UserProfile" in analysis["definitions"]
    assert "getUser" in analysis["definitions"]
    assert "fetchUser" in analysis["calls"]


def test_go_symbol_extraction():
    code = b"""
package main

func ProcessOrder(order Order) float64 {
    return CalculateTax(order.Total, 0.05)
}
"""
    analysis = extract_symbol_analysis(code, [4, 5], language="go")
    assert "ProcessOrder" in analysis["definitions"]
    assert "CalculateTax" in analysis["calls"]


def test_rust_symbol_extraction():
    code = b"""
fn process_order(order: &Order) -> f64 {
    calculate_tax(order.total, 0.05)
}

struct OrderManager {
    orders: Vec<Order>,
}
"""
    analysis = extract_symbol_analysis(code, [2, 3, 6], language="rust")
    assert "process_order" in analysis["definitions"]
    assert "calculate_tax" in analysis["calls"]


def test_java_symbol_extraction():
    code = b"""
public class OrderService {
    public double processOrder(Order order) {
        return calculateTax(order.getTotal(), 0.05);
    }
}
"""
    analysis = extract_symbol_analysis(code, [2, 3, 4], language="java")
    assert "OrderService" in analysis["definitions"]
    assert "processOrder" in analysis["definitions"]


def test_extract_hunks_per_file():
    diff = (
        "diff --git a/app.js b/app.js\n"
        "--- a/app.js\n"
        "+++ b/app.js\n"
        "@@ -1,3 +1,3 @@\n"
        " function hello() {\n"
        "-    return 'old';\n"
        "+    return 'new';\n"
        " }\n"
        "diff --git a/utils.py b/utils.py\n"
        "--- a/utils.py\n"
        "+++ b/utils.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def helper():\n"
        "-    return 0\n"
        "+    return 1\n"
    )
    hunks = extract_hunks_per_file(diff)
    assert "app.js" in hunks
    assert "utils.py" in hunks
    assert "return 'new';" in hunks["app.js"]
    assert "return 1" in hunks["utils.py"]


def test_cross_language_conflict_detection():
    """Two JS patches modifying the same function should conflict."""
    from graphmerge.mcp_server import arbitrate_diff_patches_core

    diff_a = (
        "diff --git a/app.js b/app.js\n"
        "--- a/app.js\n"
        "+++ b/app.js\n"
        "@@ -1,3 +1,3 @@\n"
        " function processOrder(order) {\n"
        "-    return order.total;\n"
        "+    return order.total * 1.1;\n"
        " }\n"
    )
    diff_b = (
        "diff --git a/app.js b/app.js\n"
        "--- a/app.js\n"
        "+++ b/app.js\n"
        "@@ -1,3 +1,3 @@\n"
        " function processOrder(order) {\n"
        "-    return order.total;\n"
        "+    return order.total * 1.2;\n"
        " }\n"
    )
    result = arbitrate_diff_patches_core(
        [
            {"id": "js_a", "diff": diff_a, "weight": 10.0},
            {"id": "js_b", "diff": diff_b, "weight": 5.0},
        ]
    )
    assert result["status"] == "success"
    assert result["total_conflict_edges"] > 0
    assert "js_a" in result["accepted_patches"]
    assert "js_b" in result["deferred_patches"]


def test_merged_diff_output():
    """Accepted patches should appear in merged_diff."""
    from graphmerge.mcp_server import arbitrate_diff_patches_core

    diff_a = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def f():\n"
        "-    return 1\n"
        "+    return 2\n"
    )
    diff_b = (
        "diff --git a/b.py b/b.py\n"
        "--- a/b.py\n"
        "+++ b/b.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def g():\n"
        "-    return 3\n"
        "+    return 4\n"
    )
    result = arbitrate_diff_patches_core(
        [
            {"id": "p1", "diff": diff_a, "weight": 10.0},
            {"id": "p2", "diff": diff_b, "weight": 5.0},
        ]
    )
    assert "merged_diff" in result
    assert "return 2" in result["merged_diff"]
    assert "return 4" in result["merged_diff"]


def test_js_syntax_validation():
    valid_js_diff = (
        "diff --git a/app.js b/app.js\n"
        "--- a/app.js\n"
        "+++ b/app.js\n"
        "@@ -1,2 +1,2 @@\n"
        "-const x = 1;\n"
        "+const x = 2;\n"
    )
    assert validate_diff_syntax(valid_js_diff) is True

    broken_js_diff = (
        "diff --git a/app.js b/app.js\n"
        "--- a/app.js\n"
        "+++ b/app.js\n"
        "@@ -1,2 +1,2 @@\n"
        "+function broken( {\n"
    )
    assert validate_diff_syntax(broken_js_diff) is False
