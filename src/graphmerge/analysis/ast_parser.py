import re
import hashlib
from typing import Set, List, Dict, Optional, Any

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


def extract_symbols_from_source(file_content: bytes, modified_lines: List[int]) -> Set[str]:
    """Uses cached Tree-Sitter AST to find all function, class, and method symbols

    enclosing the modified line ranges in high speed.
    """
    if not modified_lines:
        return set()

    if not TREE_SITTER_AVAILABLE or _parser is None:
        return _regex_fallback_symbol_scanner(file_content, modified_lines)

    # Use hash of file bytes for instant tree cache lookup
    cache_key = hashlib.sha256(file_content).hexdigest()
    if cache_key in _AST_CACHE:
        tree = _AST_CACHE[cache_key]
    else:
        tree = _parser.parse(file_content)
        _AST_CACHE[cache_key] = tree

    symbols: Set[str] = set()
    mod_set = set(modified_lines)

    def traverse(node):
        # Quick bounding box check: if node line range doesn't touch any modified line, skip subtree
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1

        # Check if any modified line falls inside [node_start, node_end]
        if not any(node_start <= line <= node_end for line in mod_set):
            return

        if node.type in ("function_definition", "class_definition"):
            for child in node.children:
                if child.type == "identifier":
                    symbols.add(child.text.decode("utf-8"))
                    break

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return symbols


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
