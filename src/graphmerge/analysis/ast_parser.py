import ast
import bisect
import hashlib
import os
import re
import textwrap
import threading
from collections import OrderedDict
from typing import TypedDict


class _BoundedCache(OrderedDict):
    def __init__(self, maxsize=256):
        super().__init__()
        self.maxsize = maxsize
        self._lock = threading.RLock()

    def __setitem__(self, key, value):
        with self._lock:
            if key in self:
                self.move_to_end(key)
            super().__setitem__(key, value)
            if len(self) > self.maxsize:
                self.popitem(last=False)

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)


class SymbolAnalysis(TypedDict, total=False):
    definitions: set[str]
    calls: set[str]
    imports: set[str]


# ---------------------------------------------------------------------------
# Tree-sitter multi-language setup
# ---------------------------------------------------------------------------

_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
}

# Per-language tree-sitter node-type config.
# Each entry: (node_types_that_define, child_type_holding_name)
# For calls: (call_node_type, [possible child types for callee name])
# For imports: (import_node_types, child_types_for_imported_name)
_LANG_NODE_CFG: dict[str, dict] = {
    "python": {
        "def_types": {
            "function_definition": "identifier",
            "class_definition": "identifier",
        },
        "call_type": "call",
        "call_name_types": ("identifier", "attribute"),
        "import_types": {
            "import_statement": "dotted_name",
            "import_from_statement": "dotted_name",
        },
    },
    "javascript": {
        "def_types": {
            "function_declaration": "identifier",
            "class_declaration": "identifier",
            "method_definition": "property_identifier",
        },
        "call_type": "call_expression",
        "call_name_types": ("identifier", "member_expression"),
        "import_types": {
            "import_statement": "identifier",
        },
    },
    "typescript": {
        "def_types": {
            "function_declaration": "identifier",
            "class_declaration": "identifier",
            "method_definition": "property_identifier",
            "interface_declaration": "type_identifier",
            "type_alias_declaration": "type_identifier",
            "enum_declaration": "identifier",
        },
        "call_type": "call_expression",
        "call_name_types": ("identifier", "member_expression"),
        "import_types": {
            "import_statement": "identifier",
        },
    },
    "tsx": {
        "def_types": {
            "function_declaration": "identifier",
            "class_declaration": "identifier",
            "method_definition": "property_identifier",
            "interface_declaration": "type_identifier",
            "type_alias_declaration": "type_identifier",
            "enum_declaration": "identifier",
        },
        "call_type": "call_expression",
        "call_name_types": ("identifier", "member_expression"),
        "import_types": {
            "import_statement": "identifier",
        },
    },
    "go": {
        "def_types": {
            "function_declaration": "identifier",
            "method_declaration": "field_identifier",
            "type_spec": "type_identifier",
        },
        "call_type": "call_expression",
        "call_name_types": ("identifier", "selector_expression"),
        "import_types": {
            "import_declaration": "interpreted_string_literal",
        },
    },
    "rust": {
        "def_types": {
            "function_item": "identifier",
            "struct_item": "type_identifier",
            "enum_item": "type_identifier",
            "trait_item": "type_identifier",
            "impl_item": "type_identifier",
        },
        "call_type": "call_expression",
        "call_name_types": ("identifier", "field_expression"),
        "import_types": {
            "use_declaration": "identifier",
        },
    },
    "java": {
        "def_types": {
            "method_declaration": "identifier",
            "class_declaration": "identifier",
            "interface_declaration": "identifier",
            "constructor_declaration": "identifier",
        },
        "call_type": "method_invocation",
        "call_name_types": ("identifier",),
        "import_types": {
            "import_declaration": "identifier",
        },
    },
}

# Lazily loaded parsers: lang_name -> (Parser, Language)
_LANG_PARSERS: dict[str, tuple] = {}
_parser_init_lock = threading.Lock()


def _get_parser(lang: str):
    if lang in _LANG_PARSERS:
        return _LANG_PARSERS[lang]
    with _parser_init_lock:
        if lang in _LANG_PARSERS:
            return _LANG_PARSERS[lang]
        try:
            from tree_sitter import Language, Parser

            if lang == "python":
                import tree_sitter_python as mod

                ts_lang = Language(mod.language())
            elif lang == "javascript":
                import tree_sitter_javascript as mod

                ts_lang = Language(mod.language())
            elif lang == "typescript":
                import tree_sitter_typescript as mod

                ts_lang = Language(mod.language_typescript())
            elif lang == "tsx":
                import tree_sitter_typescript as mod

                ts_lang = Language(mod.language_tsx())
            elif lang == "go":
                import tree_sitter_go as mod

                ts_lang = Language(mod.language())
            elif lang == "rust":
                import tree_sitter_rust as mod

                ts_lang = Language(mod.language())
            elif lang == "java":
                import tree_sitter_java as mod

                ts_lang = Language(mod.language())
            else:
                _LANG_PARSERS[lang] = (None, None)
                return None, None

            p = Parser(ts_lang)
            _LANG_PARSERS[lang] = (p, ts_lang)
            return p, ts_lang
        except ImportError:
            _LANG_PARSERS[lang] = (None, None)
            return None, None


# Eagerly init Python parser for backward compat
try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    PY_LANGUAGE = Language(tspython.language())
    _parser = Parser(PY_LANGUAGE)
    TREE_SITTER_AVAILABLE = True
    _LANG_PARSERS["python"] = (_parser, PY_LANGUAGE)
except ImportError:
    TREE_SITTER_AVAILABLE = False
    _parser = None

_AST_CACHE: _BoundedCache = _BoundedCache(256)


def detect_language(file_path: str) -> str:
    """Detects programming language from file extension."""
    _, ext = os.path.splitext(file_path)
    return _EXT_TO_LANG.get(ext.lower(), "python")


# ---------------------------------------------------------------------------
# Diff parsing utilities
# ---------------------------------------------------------------------------


def extract_modified_lines(diff_text: str) -> dict[str, list[int]]:
    """Parses a unified diff to extract *added* line numbers per file."""
    files_modified: dict[str, list[int]] = {}
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
                continue
            else:
                new_line += 1

    return files_modified


def extract_hunk_code(diff_text: str) -> str:
    """Reconstructs readable code from unified diff hunks."""
    lines = []
    for line in diff_text.splitlines():
        if line.startswith(("diff --git", "--- ", "+++ ", "@@", "index ")):
            continue
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


def extract_hunks_per_file(diff_text: str) -> dict[str, str]:
    """Extracts reconstructed code per file from a unified diff."""
    file_lines: dict[str, list[str]] = {}
    current_file: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            file_lines.setdefault(current_file, [])
            continue
        if line.startswith(("diff --git", "--- ", "@@", "index ", "\\")):
            continue
        if current_file is None:
            continue
        if line.startswith("-"):
            continue
        if line.startswith("+"):
            file_lines[current_file].append(line[1:])
        elif line.startswith(" "):
            file_lines[current_file].append(line[1:])
        else:
            file_lines[current_file].append(line)

    return {fp: "\n".join(lines) for fp, lines in file_lines.items()}


# ---------------------------------------------------------------------------
# Multi-language tree-sitter symbol analysis
# ---------------------------------------------------------------------------


def _ts_extract_name(node) -> str | None:
    """Extracts the text of a tree-sitter node as a decoded string."""
    if node.text:
        return node.text.decode("utf-8", errors="ignore")
    return None


def _ts_find_child_type(node, child_type: str) -> str | None:
    """Finds the first child of a given type and returns its text."""
    for child in node.children:
        if child.type == child_type:
            return _ts_extract_name(child)
    return None


def _ts_extract_callee_name(node, name_types: tuple[str, ...]) -> str | None:
    """Extracts function/method name from a call node's first child."""
    if not node.children:
        return None
    fn_node = node.children[0]
    if fn_node.type in name_types:
        if fn_node.type == "identifier":
            return _ts_extract_name(fn_node)
        # For attribute/member/selector access, get last identifier
        for sub in reversed(fn_node.children):
            if sub.type in (
                "identifier",
                "property_identifier",
                "field_identifier",
            ):
                return _ts_extract_name(sub)
    return None


def extract_symbol_analysis(
    file_content: bytes,
    modified_lines: list[int],
    language: str = "python",
) -> SymbolAnalysis:
    """Two-tier AST analysis supporting multiple languages.

    1. Definitions: Functions/classes/types modified or enclosed by the diff.
    2. Calls: Functions/methods invoked within modified lines.
    3. Imports: Modules/symbols imported within modified lines.
    """
    if not modified_lines:
        return {"definitions": set(), "calls": set(), "imports": set()}

    # Try tree-sitter for the requested language
    parser, _ = _get_parser(language)
    if parser is not None:
        cfg = _LANG_NODE_CFG.get(language)
        if cfg:
            return _ts_symbol_analysis(parser, file_content, modified_lines, cfg, language)

    # Fallback: Python ast module (only works for Python)
    if language == "python":
        if TREE_SITTER_AVAILABLE and _parser is not None:
            return _ts_symbol_analysis(
                _parser, file_content, modified_lines, _LANG_NODE_CFG["python"], "python"
            )
        return _python_ast_fallback_analysis(file_content, modified_lines)

    # Non-Python without tree-sitter: regex fallback
    return _regex_generic_analysis(file_content, modified_lines)


def _ts_symbol_analysis(
    parser,
    file_content: bytes,
    modified_lines: list[int],
    cfg: dict,
    language: str = "",
) -> SymbolAnalysis:
    """Generic tree-sitter analysis using per-language node config."""
    h = hashlib.sha256(file_content)
    h.update(language.encode("utf-8"))
    cache_key = h.hexdigest()
    if cache_key in _AST_CACHE:
        tree = _AST_CACHE[cache_key]
    else:
        tree = parser.parse(file_content)
        _AST_CACHE[cache_key] = tree

    definitions: set[str] = set()
    calls: set[str] = set()
    imports: set[str] = set()
    mod_set = set(modified_lines)
    sorted_mod_lines = sorted(mod_set)

    def_types: dict[str, str] = cfg["def_types"]
    call_type: str = cfg["call_type"]
    call_name_types: tuple = cfg["call_name_types"]
    import_types: dict[str, str] = cfg["import_types"]

    def range_intersects(start, end):
        i = bisect.bisect_left(sorted_mod_lines, start)
        return i < len(sorted_mod_lines) and sorted_mod_lines[i] <= end

    def traverse(node):
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1

        if not range_intersects(node_start, node_end):
            return

        # Definitions
        if node.type in def_types:
            name_type = def_types[node.type]
            name = _ts_find_child_type(node, name_type)
            if name:
                definitions.add(name)

        # Calls
        if node.type == call_type:
            call_line = node.start_point[0] + 1
            if call_line in mod_set and node.children:
                name = _ts_extract_callee_name(node, call_name_types)
                if name:
                    calls.add(name)

        # Imports
        if node.type in import_types:
            stmt_line = node.start_point[0] + 1
            if stmt_line in mod_set:
                target_type = import_types[node.type]
                _collect_import_names(node, target_type, imports)

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return {"definitions": definitions, "calls": calls, "imports": imports}


def _collect_import_names(node, target_type: str, imports: set[str]):
    """Recursively collects import name nodes of the target type."""
    if node.type == target_type:
        name = _ts_extract_name(node)
        if name:
            imports.add(name.strip('"').strip("'"))
        return
    for child in node.children:
        _collect_import_names(child, target_type, imports)


def _regex_generic_analysis(file_content: bytes, modified_lines: list[int]) -> SymbolAnalysis:
    """Regex fallback for non-Python when tree-sitter is unavailable."""
    lines = file_content.decode("utf-8", errors="ignore").splitlines()
    definitions: set[str] = set()
    calls: set[str] = set()

    # Generic patterns that work across C-family languages
    def_re = re.compile(
        r"(?:def|func|function|fn|class|struct|enum|trait|interface|impl)"
        r"\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    )
    call_re = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    import_re = re.compile(r"(?:import|from|use|require)\s+[\"']?([a-zA-Z_][a-zA-Z0-9_./]*)")

    for line_num in modified_lines:
        if line_num < 1 or line_num > len(lines):
            continue
        line = lines[line_num - 1].strip()
        dm = def_re.search(line)
        if dm:
            definitions.add(dm.group(1))
        cm = call_re.findall(line)
        for c in cm:
            if c not in ("if", "for", "while", "switch", "return"):
                calls.add(c)

    # Enclosing definition scan
    for line_num in modified_lines:
        for idx in range(min(line_num - 1, len(lines) - 1), -1, -1):
            cur = lines[idx].strip()
            dm = def_re.search(cur)
            if dm:
                definitions.add(dm.group(1))
                break

    imports: set[str] = set()
    for line_num in modified_lines:
        if line_num < 1 or line_num > len(lines):
            continue
        line = lines[line_num - 1].strip()
        im = import_re.search(line)
        if im:
            imports.add(im.group(1))

    return {"definitions": definitions, "calls": calls, "imports": imports}


# ---------------------------------------------------------------------------
# Backward-compat and Python-specific helpers
# ---------------------------------------------------------------------------


def extract_symbols_from_source(file_content: bytes, modified_lines: list[int]) -> set[str]:
    """Backward-compatible helper returning modified definition symbols."""
    analysis = extract_symbol_analysis(file_content, modified_lines)
    return analysis.get("definitions", set())


def _python_ast_fallback_analysis(file_content: bytes, modified_lines: list[int]) -> SymbolAnalysis:
    """Python stdlib `ast` fallback when Tree-Sitter is unavailable."""
    definitions: set[str] = set()
    calls: set[str] = set()
    imports: set[str] = set()
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

    return {"definitions": definitions, "calls": calls, "imports": imports}


def _regex_fallback_symbol_scanner(file_content: bytes, modified_lines: list[int]) -> set[str]:
    """Lightweight regex fallback to find enclosing definitions."""
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
    """Validates syntax of added lines in a unified diff.

    For Python files, uses ast.parse. For other languages, uses
    tree-sitter parse (error node detection). Falls back to True
    for unknown languages (permissive — let the conflict graph decide).
    """
    if not diff_text or not diff_text.strip():
        return True

    lines = diff_text.splitlines()

    # Detect language from first file path in diff
    lang = "python"
    for line in lines:
        if line.startswith("+++ b/"):
            lang = detect_language(line[6:].strip())
            break

    is_diff = any(diff_text.startswith(p) for p in ("diff --git", "--- ", "+++ ", "@@ ")) or any(
        line.startswith("+") and not line.startswith("+++") for line in lines
    )

    if lang == "python":
        return _validate_python_syntax(diff_text, lines, is_diff)

    # Non-Python: use tree-sitter error node detection
    return _validate_ts_syntax(diff_text, lines, is_diff, lang)


def _validate_python_syntax(diff_text: str, lines: list[str], is_diff: bool) -> bool:
    """Python-specific syntax validation."""
    if not is_diff:
        try:
            ast.parse(diff_text)
            return True
        except SyntaxError:
            try:
                ast.parse(textwrap.dedent(diff_text))
                return True
            except SyntaxError:
                try:
                    wrapped = "def _dummy():\n" + textwrap.indent(
                        textwrap.dedent(diff_text), "    "
                    )
                    ast.parse(wrapped)
                    return True
                except SyntaxError:
                    return False
        except Exception:
            return False

    file_map: dict[str, list[str]] = {}
    current_file = None
    for line in lines:
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            file_map[current_file] = []
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            file_map[current_file].append(line[1:])

    if not file_map:
        return True

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


def _validate_ts_syntax(diff_text: str, lines: list[str], is_diff: bool, lang: str) -> bool:
    """Tree-sitter based syntax validation for non-Python languages."""
    parser, _ = _get_parser(lang)
    if parser is None:
        return True

    if not is_diff:
        tree = parser.parse(diff_text.encode("utf-8", errors="ignore"))
        return not _tree_has_error(tree.root_node)

    # Extract added lines per file
    added: list[str] = []
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])

    if not added:
        return True

    code = "\n".join(added)
    tree = parser.parse(code.encode("utf-8", errors="ignore"))
    return not _tree_has_error(tree.root_node)


def _tree_has_error(node) -> bool:
    """Checks if a tree-sitter tree contains ERROR or MISSING nodes."""
    if node.type == "ERROR" or node.is_missing:
        return True
    for child in node.children:
        if _tree_has_error(child):
            return True
    return False
