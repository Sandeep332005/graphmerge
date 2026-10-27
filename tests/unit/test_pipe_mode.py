import json
import subprocess
import sys


def test_pipe_arbitrate():
    """Tests graphmerge pipe mode with arbitration input."""
    req = {
        "action": "arbitrate",
        "patches": [
            {
                "id": "p1",
                "diff": (
                    "diff --git a/a.py b/a.py\n"
                    "--- a/a.py\n"
                    "+++ b/a.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def f():\n"
                    "-    return 1\n"
                    "+    return 2\n"
                ),
                "weight": 10.0,
            },
        ],
    }
    result = subprocess.run(
        [sys.executable, "-m", "graphmerge.cli", "pipe"],
        input=json.dumps(req),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert "p1" in data["accepted_patches"]
    assert "merged_diff" in data


def test_pipe_check():
    """Tests graphmerge pipe mode with collision check."""
    req = {
        "action": "check",
        "diff_a": (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def f():\n"
            "-    return 1\n"
            "+    return 2\n"
        ),
        "diff_b": (
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def g():\n"
            "-    return 3\n"
            "+    return 4\n"
        ),
    }
    result = subprocess.run(
        [sys.executable, "-m", "graphmerge.cli", "pipe"],
        input=json.dumps(req),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["has_conflict"] is False


def test_pipe_stream_mode():
    """Tests JSONL streaming mode."""
    lines = []
    for i in range(3):
        req = {
            "action": "arbitrate",
            "patches": [
                {
                    "id": f"p{i}",
                    "diff": (
                        f"diff --git a/f{i}.py b/f{i}.py\n"
                        f"--- a/f{i}.py\n"
                        f"+++ b/f{i}.py\n"
                        f"@@ -1,2 +1,2 @@\n"
                        f" def func{i}():\n"
                        f"-    return 0\n"
                        f"+    return {i}\n"
                    ),
                    "weight": 1.0,
                }
            ],
        }
        lines.append(json.dumps(req))
    input_text = "\n".join(lines) + "\n"

    result = subprocess.run(
        [sys.executable, "-m", "graphmerge.cli", "pipe", "--stream"],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    output_lines = [ln for ln in result.stdout.strip().split("\n") if ln.strip()]
    assert len(output_lines) == 3
    for line in output_lines:
        data = json.loads(line)
        assert data["status"] == "success"
