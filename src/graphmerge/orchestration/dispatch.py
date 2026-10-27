"""Pluggable agent worker dispatch for the fanout node.

Provides a base protocol and concrete implementations:
- CallbackWorker: wraps any callable (function, lambda, API call)
- SubprocessWorker: runs an external command per task
- PassthroughWorker: returns pre-loaded proposals (testing/default)

To integrate with LangGraph Send API, CrewAI, AutoGen, etc.,
implement the AgentWorker protocol.
"""

import json
import logging
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Protocol

log = logging.getLogger("graphmerge")


class AgentWorker(Protocol):
    """Protocol for agent workers that generate patch proposals."""

    def generate_proposal(
        self,
        task: dict[str, Any],
        baseline: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Generates a patch proposal for the given task.

        Args:
            task: Task spec with at least {id, description, target_files}.
            baseline: Current baseline version (commit SHA or s_N).
            context: Optional collision context from prior iteration.

        Returns:
            AgentProposal dict with {id, diff_content, verified_local_gain, ...}
            or None if the worker cannot produce a proposal.
        """
        ...


class PassthroughWorker:
    """Returns pre-loaded proposals without modification. Default behavior."""

    def __init__(self, proposals: list[dict[str, Any]] | None = None):
        self._proposals = proposals or []

    def generate_proposal(
        self,
        task: dict[str, Any],
        baseline: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        task_id = task.get("id", task.get("task_id", ""))
        for p in self._proposals:
            if p.get("id") == task_id or p.get("task_id") == task_id:
                return p
        return None


class CallbackWorker:
    """Wraps any callable as an agent worker.

    Usage:
        worker = CallbackWorker(my_llm_generate_fn)
    """

    def __init__(self, callback):
        self._callback = callback

    def generate_proposal(
        self,
        task: dict[str, Any],
        baseline: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        result = self._callback(task, baseline, context)
        if result and "id" not in result:
            result["id"] = task.get("id", str(uuid.uuid4())[:8])
        return result


class SubprocessWorker:
    """Runs an external command per task, passing JSON via stdin.

    The command receives:
        {"task": {...}, "baseline": "...", "context": {...}}

    And must return a JSON proposal on stdout:
        {"id": "...", "diff_content": "...", "verified_local_gain": 1.0}

    Usage:
        worker = SubprocessWorker("python my_agent.py")
    """

    def __init__(self, command: str, timeout: int = 300):
        self._command = command
        self._timeout = timeout

    def generate_proposal(
        self,
        task: dict[str, Any],
        baseline: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        payload = json.dumps(
            {"task": task, "baseline": baseline, "context": context},
            default=str,
        )
        try:
            result = subprocess.run(
                self._command,
                shell=True,
                input=payload,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                log.warning("Subprocess worker failed: %s", result.stderr[:200])
                return None
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            log.warning("Subprocess worker error: %s", e)
            return None


class WorkerPool:
    """Dispatches tasks to agent workers in parallel.

    Wraps ThreadPoolExecutor for concurrent proposal generation.
    """

    def __init__(self, worker: AgentWorker, max_workers: int = 8):
        self._worker = worker
        self._max_workers = max_workers

    def dispatch(
        self,
        tasks: list[dict[str, Any]],
        baseline: str,
        contexts: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Fans out tasks to workers and collects proposals.

        Args:
            tasks: List of task specs.
            baseline: Current baseline version.
            contexts: Optional per-task collision contexts keyed by task id.

        Returns:
            List of proposals (excludes None results).
        """
        contexts = contexts or {}
        proposals: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(
                    self._worker.generate_proposal,
                    task,
                    baseline,
                    contexts.get(task.get("id", "")),
                ): task
                for task in tasks
            }

            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    if result:
                        proposals.append(result)
                    else:
                        log.warning(
                            "Worker returned None for task %s",
                            task.get("id", "?"),
                        )
                except Exception as e:
                    log.warning(
                        "Worker failed for task %s: %s",
                        task.get("id", "?"),
                        e,
                    )

        log.info(
            "Dispatched %d tasks, received %d proposals",
            len(tasks),
            len(proposals),
        )
        return proposals
