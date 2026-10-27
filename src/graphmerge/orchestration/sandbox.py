"""Real sandbox execution: applies accepted patches to a git worktree,
runs an optional test command, and commits atomically on success.

Replaces the stub sandbox_integration_node.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import Any

log = logging.getLogger("graphmerge")


class SandboxError(Exception):
    pass


class GitSandbox:
    """Manages a temporary git worktree for atomic patch application."""

    def __init__(self, repo_path: str, test_command: str | None = None):
        self.repo_path = os.path.abspath(repo_path)
        self.test_command = test_command
        self._worktree_path: str | None = None
        self._branch_name: str | None = None

    def apply_patches(
        self,
        patches: list[dict[str, Any]],
        baseline: str = "HEAD",
    ) -> dict[str, Any]:
        """Applies a list of accepted patches atomically.

        1. Creates a temporary git worktree from baseline.
        2. Applies each patch via `git apply`.
        3. If test_command is set, runs it. On failure, rolls back.
        4. On success, commits and returns the new commit SHA.

        Returns dict with: commit_sha, applied_ids, failed_ids, test_passed.
        """
        applied_ids: list[str] = []
        failed_ids: list[str] = []

        if not patches:
            return {
                "commit_sha": None,
                "applied_ids": [],
                "failed_ids": [],
                "test_passed": True,
                "baseline": baseline,
            }

        self._worktree_path = tempfile.mkdtemp(prefix="graphmerge_sandbox_")
        self._branch_name = f"graphmerge-sandbox-{os.getpid()}-{uuid.uuid4().hex[:8]}"

        try:
            self._create_worktree(baseline)

            for patch in patches:
                p_id = patch.get("id", "unknown")
                diff_text = patch.get("diff_content", "")
                if not diff_text:
                    failed_ids.append(p_id)
                    continue

                if self._apply_single_patch(diff_text):
                    applied_ids.append(p_id)
                else:
                    failed_ids.append(p_id)
                    log.warning("Patch %s failed to apply cleanly", p_id)

            if not applied_ids:
                return {
                    "commit_sha": None,
                    "applied_ids": [],
                    "failed_ids": failed_ids,
                    "test_passed": False,
                    "baseline": baseline,
                }

            test_passed = self._run_tests() if self.test_command else True

            if test_passed:
                commit_sha = self._commit(applied_ids)
                return {
                    "commit_sha": commit_sha,
                    "applied_ids": applied_ids,
                    "failed_ids": failed_ids,
                    "test_passed": True,
                    "baseline": baseline,
                }
            else:
                log.warning("Test command failed after applying patches")
                return {
                    "commit_sha": None,
                    "applied_ids": applied_ids,
                    "failed_ids": failed_ids,
                    "test_passed": False,
                    "baseline": baseline,
                }

        finally:
            self._cleanup()

    def _git(self, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        cmd = ["git"] + list(args)
        return subprocess.run(
            cmd,
            cwd=cwd or self._worktree_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def _create_worktree(self, baseline: str):
        result = self._git(
            "worktree",
            "add",
            "-b",
            self._branch_name,
            self._worktree_path,
            baseline,
            cwd=self.repo_path,
        )
        if result.returncode != 0:
            raise SandboxError(f"Failed to create worktree: {result.stderr}")

    def _apply_single_patch(self, diff_text: str) -> bool:
        """Applies a unified diff via git apply. Returns True on success."""
        patch_file = os.path.join(self._worktree_path, ".graphmerge_patch.diff")
        try:
            with open(patch_file, "w", encoding="utf-8") as f:
                f.write(diff_text)

            result = self._git("apply", "--check", patch_file)
            if result.returncode != 0:
                return False

            result = self._git("apply", patch_file)
            return result.returncode == 0
        finally:
            if os.path.exists(patch_file):
                os.remove(patch_file)

    def _run_tests(self) -> bool:
        if not self.test_command:
            return True
        result = subprocess.run(
            self.test_command,
            shell=True,
            cwd=self._worktree_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            log.warning("Test output:\n%s\n%s", result.stdout[-500:], result.stderr[-500:])
        return result.returncode == 0

    def _commit(self, applied_ids: list[str]) -> str | None:
        self._git("add", "-A")
        ids_str = ", ".join(applied_ids)
        msg = f"GraphMerge: apply accepted patches [{ids_str}]"
        result = self._git("commit", "-m", msg)
        if result.returncode != 0:
            log.warning("Commit failed: %s", result.stderr)
            return None
        rev = self._git("rev-parse", "HEAD")
        return rev.stdout.strip() if rev.returncode == 0 else None

    def _cleanup(self):
        if self._worktree_path and os.path.isdir(self._worktree_path):
            self._git(
                "worktree",
                "remove",
                "--force",
                self._worktree_path,
                cwd=self.repo_path,
            )
            if os.path.isdir(self._worktree_path):
                shutil.rmtree(self._worktree_path, ignore_errors=True)
        if self._branch_name:
            self._git("branch", "-D", self._branch_name, cwd=self.repo_path)


def sandbox_integration_node_real(state: dict[str, Any]) -> dict[str, Any]:
    """Production sandbox node — applies patches via git worktree.

    Falls back to the stub behavior if workspace_path is not a git repo.
    """
    newly_accepted = state.get("newly_accepted", [])
    accumulated_accepted = list(state.get("accepted_patches", []))
    staged = state.get("staged_patches", [])
    workspace = state.get("workspace_path", "")
    test_cmd = state.get("test_command")
    new_iter = state.get("iteration", 0) + 1
    max_iter = state.get("max_iterations", 3)

    git_dir = os.path.join(workspace, ".git") if workspace else ""
    is_git = workspace and os.path.isdir(git_dir)

    if is_git and newly_accepted:
        baseline = state.get("current_baseline", "HEAD")
        if baseline.startswith("s_"):
            baseline = "HEAD"

        sandbox = GitSandbox(workspace, test_command=test_cmd)
        result = sandbox.apply_patches(newly_accepted, baseline)

        commit_sha = result.get("commit_sha")
        test_passed = result.get("test_passed", False)

        if test_passed and commit_sha:
            new_baseline = commit_sha
            applied_set = set(result.get("applied_ids", []))
            for p in newly_accepted:
                if p.get("id") in applied_set:
                    accumulated_accepted.append(p)
                else:
                    staged.append(p)
        else:
            staged.extend(newly_accepted)
            new_baseline = f"s_{new_iter}"
    else:
        accumulated_accepted.extend(newly_accepted)
        new_baseline = f"s_{new_iter}"

    is_converged = len(staged) == 0 or new_iter >= max_iter

    return {
        "current_baseline": new_baseline,
        "accepted_patches": accumulated_accepted,
        "staged_patches": staged,
        "iteration": new_iter,
        "is_converged": is_converged,
    }
