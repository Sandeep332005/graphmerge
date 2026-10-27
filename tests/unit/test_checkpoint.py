import os
import tempfile

from graphmerge.orchestration.checkpoint import CheckpointStore


def test_save_and_load():
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        state = {
            "iteration": 2,
            "accepted_patches": [{"id": "p1"}],
            "is_converged": False,
            "touched_symbols": {"a.py": {"foo", "bar"}},
        }
        store.save("run-1", state)
        loaded = store.load("run-1")
        assert loaded is not None
        assert loaded["iteration"] == 2
        assert loaded["accepted_patches"] == [{"id": "p1"}]
        assert loaded["touched_symbols"]["a.py"] == {"bar", "foo"}


def test_load_missing():
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        assert store.load("nonexistent") is None


def test_list_runs():
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        store.save("r1", {"iteration": 1, "is_converged": False})
        store.save("r2", {"iteration": 3, "is_converged": True})
        runs = store.list_runs()
        assert len(runs) == 2
        ids = {r["run_id"] for r in runs}
        assert ids == {"r1", "r2"}


def test_delete():
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        store.save("r1", {"iteration": 0})
        assert store.delete("r1") is True
        assert store.load("r1") is None
        assert store.delete("r1") is False


def test_set_roundtrip():
    """Sets survive JSON serialization via __set__ wrapper."""
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        state = {"data": {"nested": {"symbols": {"x", "y", "z"}}}}
        store.save("s1", state)
        loaded = store.load("s1")
        assert loaded["data"]["nested"]["symbols"] == {"x", "y", "z"}
        assert isinstance(loaded["data"]["nested"]["symbols"], set)


def test_atomic_write():
    """No .tmp file remains after save."""
    with tempfile.TemporaryDirectory() as d:
        store = CheckpointStore(d)
        store.save("r1", {"iteration": 0})
        files = os.listdir(d)
        assert all(not f.endswith(".tmp") for f in files)
        assert "r1.json" in files
