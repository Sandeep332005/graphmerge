import re
import ast
import hashlib
from typing import Set, List, Dict, Optional, Any
from graphmerge.orchestration.state import SymbolAnalysis

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser
    PY_LANGUAGE = Language(tspython.language())
    _parser = Parser(PY_LANGUAGE)
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    _parser = None

# Cache parsed trees by sha256 to eliminate redundant tree-sitter parses
_AST_CACHE: Dict[str, Any] = {}


def extract_modified_lines(diff_text: str) -> Dict[str, List[int]]:
    """Parses a unified diff string to extract modified line numbers per file.

    Complexity: O(L) single-pass scan of diff lines.
    """
    files_modified: Dict[str, List[int]] = {}
    current_file = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            files_modified[current_file] = []
        elif line.startswith("@@ ") and current_file:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start_line = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                files_modified[current_file].extend(range(start_line, start_line + count))

    return files_modified


def extract_symbol_analysis(file_content: bytes, modified_lines: List[int]) -> SymbolAnalysis:
    """Performs deep two-tier AST analysis on the file content against modified lines:

    1. Definitions: Functions and classes modified or enclosed by the diff.
    2. Calls: Functions or methods invoked within modified lines.
    3. Imports: Modules or symbol names imported within modified lines.
    """
    if not modified_lines:
        return {"definitions": set(), "calls": set(), "imports": set()}

    if not TREE_SITTER_AVAILABLE or _parser is None:
        return _python_ast_fallback_analysis(file_content, modified_lines)

    # Use hash of file bytes for instant tree cache lookup
    cache_key = hashlib.sha256(file_content).hexdigest()
    if cache_key in _AST_CACHE:
        tree = _AST_CACHE[cache_key]
    else:
        tree = _parser.parse(file_content)
        _AST_CACHE[cache_key] = tree

    definitions: Set[str] = set()
    calls: Set[str] = set()
    imports: Set[str] = set()
    mod_set = set(modified_lines)

    def traverse(node):
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1

        # Check if node line range intersects modified lines
        touches_diff = any(node_start <= line <= node_end for line in mod_set)
        if not touches_diff:
            return

        # 1. Definitions (Functions, Methods, Classes)
        if node.type in ("function_definition", "class_definition"):
            for child in node.children:
                if child.type == "identifier":
                    definitions.add(child.text.decode("utf-8", errors="ignore"))
                    break

        # 2. Calls (invocations inside modified lines)
        if node.type == "call":
            call_line = node.start_point[0] + 1
            if call_line in mod_set and len(node.children) > 0:
                fn_node = node.children[0]
                if fn_node.type == "identifier":
                    calls.add(fn_node.text.decode("utf-8", errors="ignore"))
                elif fn_node.type == "attribute":
                    # For obj.method(), record the method identifier
                    for sub in reversed(fn_node.children):
                        if sub.type == "identifier":
                            calls.add(sub.text.decode("utf-8", errors="ignore"))
                            break

        # 3. Imports
        if node.type in ("import_statement", "import_from_statement"):
            stmt_line = node.start_point[0] + 1
            if stmt_line in mod_set:
                for child in node.children:
                    if child.type == "dotted_name":
                        imports.add(child.text.decode("utf-8", errors="ignore"))

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return {
        "definitions": definitions,
        "calls": calls,
        "imports": imports,
    }


def extract_symbols_from_source(file_content: bytes, modified_lines: List[int]) -> Set[str]:
    """Backward-compatible helper returning the set of modified definition symbols."""
    analysis = extract_symbol_analysis(file_content, modified_lines)
    return analysis.get("definitions", set())


def _python_ast_fallback_analysis(file_content: bytes, modified_lines: List[int]) -> SymbolAnalysis:
    """Python standard library `ast` fallback when Tree-Sitter is unavailable."""
    definitions: Set[str] = set()
    calls: Set[str] = set()
    imports: Set[str] = set()
    mod_set = set(modified_lines)

    try:
        source_code = file_content.decode("utf-8", errors="ignore")
        tree = ast.parse(source_code)
    except Exception:
        # Regex emergency fallback
        return {
            "definitions": _regex_fallback_symbol_scanner(file_content, modified_lines),
            "calls": set(),
            "imports": set(),
        }

    for node in ast.walk(tree):
        if hasattr(node, "lineno"):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            touches_diff = any(node.lineno <= line <= end_lineno for line in mod_set)

            if touches_diff:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    definitions.add(node.name)

                if node.lineno in mod_set:
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            calls.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            calls.add(node.func.attr)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            imports.add(alias.name)

    return {
        "definitions": definitions,
        "calls": calls,
        "imports": imports,
    }


def _regex_fallback_symbol_scanner(file_content: bytes, modified_lines: List[int]) -> Set[str]:
    """Lightweight regex-based fallback to find enclosing definitions."""
    symbols = set()
    lines = file_content.decode("utf-8", errors="ignore").splitlines()
    for line_num in modified_lines:
        for idx in range(min(line_num - 1, len(lines) - 1), -1, -1):
            cur = lines[idx].strip()
            if cur.startswith("def ") or cur.startswith("class "):
                match = re.search(r"(?:def|class)\s+([a-zA-Z0-9_]+)", cur)
                if match:
                    symbols.add(match.group(1))
                    break
    return symbols


def validate_source_syntax(source_bytes: bytes) -> bool:
    """Fast check whether Python source code is syntactically valid."""
    try:
        ast.parse(source_bytes.decode("utf-8", errors="ignore"))
        return True
    except SyntaxError:
        return False
    except Exception:
        return False


def validate_diff_syntax(diff_text: str) -> bool:
    """Extracts added/modified lines from a unified diff or code snippet
    and verifies whether they represent syntactically valid Python.
    """
    if not diff_text or not diff_text.strip():
        return True

    lines = diff_text.splitlines()
    is_diff = any(diff_text.startswith(p) for p in ("diff --git", "--- ", "+++ ", "@@ ")) or any(
        line.startswith("+") and not line.startswith("+++") for line in lines
    )

    import textwrap

    if not is_diff:
        # Raw Python code snippet
        try:
            ast.parse(diff_text)
            return True
        except SyntaxError:
            try:
                ast.parse(textwrap.dedent(diff_text))
                return True
            except SyntaxError:
                try:
                    wrapped = "def _dummy():\n" + textwrap.indent(textwrap.dedent(diff_text), "    ")
                    ast.parse(wrapped)
                    return True
                except SyntaxError:
                    return False
        except Exception:
            return False

    # Extract lines starting with '+' (excluding '+++')
    added_lines = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    if not added_lines:
        return True

    snippet = "\n".join(added_lines)
    try:
        ast.parse(snippet)
        return True
    except SyntaxError:
        try:
            ast.parse(textwrap.dedent(snippet))
            return True
        except SyntaxError:
            try:
                wrapped = "def _dummy():\n" + textwrap.indent(textwrap.dedent(snippet), "    ")
                ast.parse(wrapped)
                return True
            except SyntaxError:
                return False
    except Exception:
        return False
