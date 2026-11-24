"""
GraphMerge: Parallel AI Agent Collaboration via Graph-Structured Distributed Block Optimization.
Reference implementation of arXiv:2610.30074.
"""

from .mcp_server import (
    arbitrate_diff_patches_core as arbitrate,
    check_patch_collision_core as check_collision,
)
from .optimization.solver import ConflictGraphOptimizer
from .analysis.ast_parser import validate_diff_syntax

__version__ = "0.1.0"
__author__ = "GraphMerge Contributors"

__all__ = [
    "arbitrate",
    "check_collision",
    "ConflictGraphOptimizer",
    "validate_diff_syntax",
    "__version__",
]
