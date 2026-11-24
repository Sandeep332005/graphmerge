"""Unit tests for GraphMerge CLI commands."""
import io
import json
import sys
from unittest.mock import patch

from graphmerge.cli import main


def test_cli_demo_text_output():
    """Verifies that `graphmerge demo` runs and displays the AST conflict dashboard."""
    with patch.object(sys, "argv", ["graphmerge", "demo"]):
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            main()
        out = captured.getvalue()
        assert "GraphMerge: Distributed Block Optimization Demo" in out
        assert "agent-alpha" in out
        assert "agent-beta" in out
        assert "Accepted Patches:" in out
        assert "Theoretical Guarantee:" in out


def test_cli_demo_json_output():
    """Verifies that `graphmerge demo --json` outputs valid arbitration JSON."""
    with patch.object(sys, "argv", ["graphmerge", "demo", "--json"]):
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            main()
        data = json.loads(captured.getvalue())
        assert data["status"] == "success"
        assert "agent-beta" in data["accepted_patches"]
        assert "agent-gamma" in data["accepted_patches"]
        assert "agent-alpha" in data["deferred_patches"]
        assert data["total_conflict_edges"] == 1
