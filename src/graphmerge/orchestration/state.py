from typing import TypedDict, List, Dict, Set, Any, Optional


class AgentProposal(TypedDict):
    id: str
    agent_id: str
    task_id: str
    diff_content: str
    target_files: List[str]
    touched_symbols: Dict[str, Set[str]]
    verified_local_gain: float


class GraphMergeState(TypedDict):
    workspace_path: str
    iteration: int
    max_iterations: int
    active_backlog: List[Dict[str, Any]]
    proposals: List[AgentProposal]
    accepted_patches: List[AgentProposal]
    staged_patches: List[AgentProposal]
    is_converged: bool
    summary_report: Optional[Dict[str, Any]]
