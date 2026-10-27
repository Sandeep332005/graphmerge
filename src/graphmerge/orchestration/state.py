from typing import Any, TypedDict

from graphmerge.analysis.ast_parser import SymbolAnalysis


class LocalVerification(TypedDict, total=False):
    status: str  # "PASSED", "FAILED", "PENDING"
    syntax_valid: bool
    tests_passed: bool
    empirical_gain: float  # Delta f_i > 0
    error_message: str | None


class CollisionContext(TypedDict, total=False):
    conflicting_proposal_ids: list[str]
    conflict_reasons: list[dict[str, Any]]
    accepted_patch_diffs: str
    reprompt_instruction: str


class AgentProposal(TypedDict, total=False):
    id: str
    agent_id: str
    task_id: str
    diff_content: str
    target_files: list[str]
    touched_symbols: dict[str, set[str]]  # File -> Set of modified symbol names
    symbol_analysis: dict[str, SymbolAnalysis]  # File -> SymbolAnalysis (defs, calls, imports)
    verified_local_gain: float
    verification: LocalVerification | None
    collision_context: CollisionContext | None
    adapted_from_id: str | None  # Reference to previous iteration proposal if re-prompted


class GraphMergeState(TypedDict, total=False):
    workspace_path: str
    test_command: str | None
    current_baseline: str  # e.g., "s_0", "s_1", or commit sha
    iteration: int
    max_iterations: int
    active_backlog: list[dict[str, Any]]
    proposals: list[AgentProposal]
    newly_accepted: list[AgentProposal]
    accepted_patches: list[AgentProposal]
    staged_patches: list[AgentProposal]
    rejected_unverified_patches: list[AgentProposal]
    is_converged: bool
    conflict_diagnostics: list[dict[str, Any]]
    summary_report: dict[str, Any] | None
