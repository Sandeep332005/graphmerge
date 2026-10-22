import re
from typing import Set, List, Dict

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser
    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


def extract_modified_lines(diff_text: str) -> Dict[str, List[int]]:
    """Parses a unified diff string to extract modified line numbers per file.

    Args:
        diff_text: Standard unified diff (e.g., from `git diff`).

    Returns:
        Dictionary mapping file paths to lists of 1-indexed modified line numbers.
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
    """Uses Tree-Sitter AST to find all function, class, and method symbols

    enclosing the modified line ranges.

    Args:
        file_content: Raw source file bytes.
        modified_lines: List of modified line numbers (1-indexed).

    Returns:
        Set of symbol identifier names.
    """
    if not TREE_SITTER_AVAILABLE:
        # Fallback to regex symbol scanner if tree-sitter bindings not installed
        return _regex_fallback_symbol_scanner(file_content, modified_lines)

    tree = parser.parse(file_content)
    symbols: Set[str] = set()

    def traverse(node):
        if node.type in ("function_definition", "class_definition"):
            node_start = node.start_point[0] + 1
            node_end = node.end_point[0] + 1

            if any(node_start <= line <= node_end for line in modified_lines):
                for child in node.children:
                    if child.type == "identifier":
                        symbols.add(child.text.decode("utf-8"))

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return symbols


def _regex_fallback_symbol_scanner(file_content: bytes, modified_lines: List[int]) -> Set[str]:
    """Lightweight regex-based fallback to find enclosing definitions."""
    symbols = set()
    lines = file_content.decode("utf-8", errors="ignore").splitlines()
    for line_num in modified_lines:
        # Walk upwards from modified line to find closest def or class
        for idx in range(min(line_num - 1, len(lines) - 1), -1, -1):
            cur = lines[idx].strip()
            if cur.startswith("def ") or cur.startswith("class "):
                match = re.search(r"(?:def|class)\s+([a-zA-Z0-9_]+)", cur)
                if match:
                    symbols.add(match.group(1))
                    break
    return symbols
