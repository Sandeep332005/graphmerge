import tempfile

from graphmerge.orchestration.supervisor import run_pipeline


def test_run_pipeline_basic():
    """Full pipeline: 2 non-conflicting patches → both accepted."""
    state = {
        "proposals": [
            {
                "id": "p1",
                "diff_content": (
                    "diff --git a/a.py b/a.py\n"
                    "--- a/a.py\n+++ b/a.py\n"
                    "@@ -1,2 +1,2 @@\n def f():\n-    return 1\n+    return 2\n"
                ),
                "verified_local_gain": 5.0,
                "touched_symbols": {"a.py": {"f"}},
            },
            {
                "id": "p2",
                "diff_content": (
                    "diff --git a/b.py b/b.py\n"
                    "--- a/b.py\n+++ b/b.py\n"
                    "@@ -1,2 +1,2 @@\n def g():\n-    return 3\n+    return 4\n"
                ),
                "verified_local_gain": 3.0,
                "touched_symbols": {"b.py": {"g"}},
            },
        ],
        "current_baseline": "s_0",
        "iteration": 0,
        "max_iterations": 3,
        "accepted_patches": [],
    }
    result = run_pipeline(state)
    accepted_ids = {p["id"] for p in result.get("accepted_patches", [])}
    assert "p1" in accepted_ids
    assert "p2" in accepted_ids
    assert result["is_converged"] is True


def test_run_pipeline_with_checkpoint():
    """Pipeline saves checkpoint when dir is provided."""
    import os

    with tempfile.TemporaryDirectory() as d:
        state = {
            "proposals": [
                {
                    "id": "p1",
                    "diff_content": (
                        "diff --git a/a.py b/a.py\n"
                        "--- a/a.py\n+++ b/a.py\n"
                        "@@ -1 +1 @@\n-x\n+y\n"
                    ),
                    "verified_local_gain": 1.0,
                    "touched_symbols": {"a.py": {"x"}},
                }
            ],
            "current_baseline": "s_0",
            "iteration": 0,
            "max_iterations": 3,
            "accepted_patches": [],
        }
        result = run_pipeline(state, run_id="test-run", checkpoint_dir=d)
        assert result["is_converged"] is True
        assert os.path.isfile(os.path.join(d, "test-run.json"))
