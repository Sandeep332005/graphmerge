import re
import ast
import hashlib
import bisect
from collections import OrderedDict
from typing import Set, List, Dict, Optional, Any, TypedDict


class _BoundedCache(OrderedDict):
    def __init__(self, maxsize=256):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)


class SymbolAnalysis(TypedDict, total=False):
    definitions: Set[str]  # Functions or classes defined / modified
    calls: Set[str]        # External or internal functions called in modified lines
    imports: Set[str]      # Modules or names imported


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
_AST_CACHE: _BoundedCache = _BoundedCache(256)


def extract_modified_lines(diff_text: str) -> Dict[str, List[int]]:
    """Parses a unified diff string to extract *added* line numbers per file.

    Only lines introduced by the patch (``+``) are recorded. Context lines
    advance the new-file line counter but are not treated as modifications,
    so unchanged code is never reported as a collision site.

    Complexity: O(L) single-pass scan of diff lines.
    """
    files_modified: Dict[str, List[int]] = {}
    current_file = None
    new_line = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            files_modified.setdefault(current_file, [])
            new_line = 0
        elif line.startswith("@@ ") and current_file:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                new_line = int(match.group(1))
        elif current_file and new_line:
            if line.startswith("+"):
                files_modified[current_file].append(new_line)
                new_line += 1
            elif line.startswith("-") or line.startswith("\\"):
                # Removed lines and diff metadata do not exist in the new file.
                continue
            else:
                # Context line: present in the new file, but not a modification.
                new_line += 1

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

    # Convert sorted list to list for bisect
    sorted_mod_lines = sorted(mod_set)

    def range_intersects(start, end):
        i = bisect.bisect_left(sorted_mod_lines, start)
        return i < len(sorted_mod_lines) and sorted_mod_lines[i] <= end

    def traverse_optimized(node):
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1

        if not range_intersects(node_start, node_end):
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
            traverse_optimized(child)

    traverse_optimized(tree.root_node)
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

    source_lines = file_content.decode("utf-8", errors="ignore").splitlines()
    sorted_mod_lines = sorted(mod_set)

    def range_intersects(start, end):
        i = bisect.bisect_left(sorted_mod_lines, start)
        return i < len(sorted_mod_lines) and sorted_mod_lines[i] <= end

    try:
        source_code = "\n".join(source_lines)
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
            if range_intersects(node.lineno, end_lineno):
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

    if not is_diff:
        # Raw Python code snippet
        import textwrap
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
    # Group added lines by file to ensure per-file syntax validation
    file_map = {}
    current_file = None
    for line in lines:
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            file_map[current_file] = []
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            file_map[current_file].append(line[1:])

    if not file_map:
        return True

    import textwrap

    def validate_snippet(snippet: str) -> bool:
        if not snippet.strip():
            return True
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

    for file_lines in file_map.values():
        if not file_lines:
            continue
        if not validate_snippet("\n".join(file_lines)):
            return False
    return True


def extract_hunk_code(diff_text: str) -> str:
    """Reconstructs readable Python code from unified diff hunks by filtering headers
    and preserving added and context lines.
    """
    lines = []
    for line in diff_text.splitlines():
        if line.startswith(("diff --git", "--- ", "+++ ", "@@", "index ")):
            continue
        # Diff metadata such as "\ No newline at end of file" is not code.
        if line.startswith("\\"):
            continue
        if line.startswith("-"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
        elif line.startswith(" "):
            lines.append(line[1:])
        else:
            lines.append(line)
    return "\n".join(lines)
