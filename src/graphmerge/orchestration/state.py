from typing import TypedDict, List, Dict, Set, Any, Optional


class LocalVerification(TypedDict, total=False):
    status: str  # "PASSED", "FAILED", "PENDING"
    syntax_valid: bool
    tests_passed: bool
    empirical_gain: float  # Delta f_i > 0
    error_message: Optional[str]


class CollisionContext(TypedDict, total=False):
    conflicting_proposal_ids: List[str]
    conflict_reasons: List[Dict[str, Any]]
    accepted_patch_diffs: str
    reprompt_instruction: str


from graphmerge.analysis.ast_parser import SymbolAnalysis


class AgentProposal(TypedDict, total=False):
    id: str
    agent_id: str
    task_id: str
    diff_content: str
    target_files: List[str]
    touched_symbols: Dict[str, Set[str]]  # File -> Set of modified symbol names
    symbol_analysis: Dict[str, SymbolAnalysis]  # File -> SymbolAnalysis (defs, calls, imports)
    verified_local_gain: float
    verification: Optional[LocalVerification]
    collision_context: Optional[CollisionContext]
    adapted_from_id: Optional[str]  # Reference to previous iteration proposal if re-prompted


class GraphMergeState(TypedDict, total=False):
    workspace_path: str
    current_baseline: str  # e.g., "s_0", "s_1", or commit sha
    iteration: int
    max_iterations: int
    active_backlog: List[Dict[str, Any]]
    proposals: List[AgentProposal]
    newly_accepted: List[AgentProposal]
    accepted_patches: List[AgentProposal]
    staged_patches: List[AgentProposal]
    rejected_unverified_patches: List[AgentProposal]
    is_converged: bool
    conflict_diagnostics: List[Dict[str, Any]]
    summary_report: Optional[Dict[str, Any]]
