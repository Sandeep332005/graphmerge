"""Pipeline state persistence — save/restore GraphMergeState to JSON.

Allows resuming arbitration across server restarts or crash recovery.
"""

import json
import logging
import os
import time
from typing import Any

log = logging.getLogger("graphmerge")


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Converts GraphMergeState to JSON-safe dict (sets → sorted lists)."""
    out: dict[str, Any] = {}
    for key, val in state.items():
        out[key] = _to_json_safe(val)
    out["_checkpoint_ts"] = time.time()
    return out


def _to_json_safe(obj):
    if isinstance(obj, set):
        return {"__set__": sorted(obj)}
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(item) for item in obj]
    return obj


def _from_json_safe(obj):
    if isinstance(obj, dict):
        if "__set__" in obj and len(obj) == 1:
            return set(obj["__set__"])
        return {k: _from_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_json_safe(item) for item in obj]
    return obj


class CheckpointStore:
    """File-backed checkpoint store for pipeline state."""

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = os.path.abspath(checkpoint_dir)
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def _path(self, run_id: str) -> str:
        safe_id = run_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.checkpoint_dir, f"{safe_id}.json")

    def save(self, run_id: str, state: dict[str, Any]) -> str:
        """Saves pipeline state. Returns the checkpoint file path."""
        path = self._path(run_id)
        data = _serialize_state(state)
        data["_run_id"] = run_id

        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, path)

        log.info("Checkpoint saved: %s (iter=%s)", run_id, state.get("iteration", "?"))
        return path

    def load(self, run_id: str) -> dict[str, Any] | None:
        """Loads pipeline state. Returns None if not found."""
        path = self._path(run_id)
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data.pop("_checkpoint_ts", None)
        data.pop("_run_id", None)
        state = _from_json_safe(data)
        log.info("Checkpoint loaded: %s (iter=%s)", run_id, state.get("iteration", "?"))
        return state

    def list_runs(self) -> list[dict[str, Any]]:
        """Lists all saved checkpoints with metadata."""
        runs = []
        for fname in os.listdir(self.checkpoint_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.checkpoint_dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                runs.append(
                    {
                        "run_id": data.get("_run_id", fname[:-5]),
                        "iteration": data.get("iteration", 0),
                        "is_converged": data.get("is_converged", False),
                        "checkpoint_ts": data.get("_checkpoint_ts", 0),
                        "path": path,
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        runs.sort(key=lambda r: r["checkpoint_ts"], reverse=True)
        return runs

    def delete(self, run_id: str) -> bool:
        """Deletes a checkpoint. Returns True if it existed."""
        path = self._path(run_id)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False
