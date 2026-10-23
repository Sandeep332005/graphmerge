---
name: graphmerge-mcp
description: Guide and operational instructions for using GraphMerge MCP Server tools (arXiv:2610.30074). Use when coordinating parallel AI coding agents, arbitrating candidate git diffs or pull requests, detecting AST collisions (Tier 1 Syntactic Definitions and Tier 2 Semantic Def-Use Call Graphs), solving Maximum Weight Independent Sets (MWIS), or generating adaptive re-prompting instructions for conflicted patches.
---

# GraphMerge MCP Server Skill

## Overview

**GraphMerge** is the reference open-source implementation of *Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization* ([arXiv:2610.30074](https://arxiv.org/abs/2610.30074), October 2026).

When multiple autonomous coding agents (Antigravity, Claude Code, Devin, SWE-agent, AutoGen) work simultaneously on a shared codebase, their independently proposed code patches often conflict. GraphMerge transforms this merge conflict dilemma into a **Discrete Block Optimization problem on a Symbol Conflict Graph $G = (V, E)$**:
* **Nodes ($V$):** Candidate diff patches proposed by parallel worker agents.
* **Edges ($E$):** AST symbol collisions detected via Tree-Sitter (Tier 1 Syntactic Definitions + Tier 2 Semantic Def-Use Call Graphs).
* **Objective:** Find the Maximum Weight Independent Set (MWIS) $\mathcal{I}^* \subseteq V$ that maximizes aggregate verified local improvement $\sum_{i \in \mathcal{I}^*} \Delta f_i$.
* **Theoretical Guarantee:** Preserves at least a $\frac{1}{\chi_f(G)}$ fraction of verified local progress in every iteration, converging geometrically across cycles.

---

## When to Use This Skill

Activate and use the `graphmerge` MCP tools whenever:
1. **Arbitrating Parallel Agent Patches:** Multiple agents, subagents, or branches propose changes simultaneously, and you need to determine which subset can be safely merged without build failures or semantic regressions.
2. **Pair-Wise Conflict Pre-Check:** You have two unified diffs and need to know whether they can apply concurrently or if they collide syntactically or semantically (`check_patch_collision`).
3. **Adaptive Re-Prompting:** An agent's patch had conflicts and was deferred; you need to provide that agent with collision diagnostics, colliding symbol names, and the diffs from the accepted patches to adapt its patch against the new baseline (`generate_reprompt_instruction`).
4. **Discrete Independent Set Solving:** Given pre-extracted symbol touch sets and empirical gain weights, compute the optimal independent set $\mathcal{I}^*$ (`solve_merge`).

---

## Available MCP Tools

The GraphMerge MCP server exposes 4 high-performance tools over `stdio` transport:

### 1. `arbitrate_diff_patches`
The primary high-level tool for end-to-end multi-agent patch arbitration.
* **Input parameter:** `diffs_json` (stringified JSON array of candidate proposals).
* **Payload schema:**
  ```json
  [
    {
      "id": "patch_1",
      "task_id": "TASK-101",
      "diff": "diff --git a/math_utils.py b/math_utils.py\n...",
      "weight": 10.0
    },
    {
      "id": "patch_2",
      "task_id": "TASK-102",
      "diff": "diff --git a/billing.py b/billing.py\n...",
      "weight": 8.0
    }
  ]
  ```
* **Processing:**
  1. Validates diff syntax.
  2. Runs Tree-Sitter AST parsing on diff hunks to extract definitions, calls, and imports.
  3. Builds Two-Tier conflict graph $G = (V, E)$ in linear $O(K \cdot S)$ time via inverted index.
  4. Solves MWIS using Divide-and-Conquer component decomposition.
* **Returns:**
  ```json
  {
    "status": "success",
    "accepted_patches": ["patch_1"],
    "deferred_patches": ["patch_2"],
    "syntax_rejected_patches": [],
    "total_patches_evaluated": 2,
    "total_conflict_edges": 1,
    "conflict_diagnostics": [
      {
        "nodes": ["patch_1", "patch_2"],
        "conflict_type": "TIER2_DEF_USE_COLLISION",
        "tier": 2,
        "symbol": "calculate_tax"
      }
    ],
    "preservation_bound": 0.5
  }
  ```

---

### 2. `check_patch_collision`
Fast pair-wise conflict analyzer between two diffs.
* **Parameters:**
  * `diff_a` (string): Unified diff or code snippet of first patch.
  * `diff_b` (string): Unified diff or code snippet of second patch.
  * `id_a` (string, optional): Identifier for patch A (default: `"patch_a"`).
  * `id_b` (string, optional): Identifier for patch B (default: `"patch_b"`).
* **Returns:**
  ```json
  {
    "has_conflict": true,
    "can_merge_concurrently": false,
    "conflict_type": "TIER1_SYNTACTIC_COLLISION",
    "tier": 1,
    "symbol": "process_order",
    "details": { ... }
  }
  ```

---

### 3. `generate_reprompt_instruction`
Generates a context-rich prompt instruction for an LLM agent worker whose patch was deferred due to AST collisions.
* **Parameters:**
  * `task_id` (string): The task identifier.
  * `colliding_patch_ids` (string): Comma-separated list of accepted patch IDs that caused the collision (e.g. `"patch_1, patch_3"`).
  * `colliding_symbols` (string): Comma-separated list of colliding symbol names (e.g. `"calculate_tax, process_order"`).
  * `baseline_version` (string, optional): The new committed baseline (default: `"s_1"`).
* **Returns:**
  ```json
  {
    "task_id": "TASK-102",
    "target_baseline": "s_1",
    "instruction": "Your prior proposed patch for task 'TASK-102' was deferred by the GraphMerge coordinator due to AST symbol collisions with patch(es) [patch_1] on symbol(s) [calculate_tax]. The accepted patch has been atomically committed into baseline s_1. Please regenerate your patch grounded in the updated symbols in s_1."
  }
  ```

---

### 4. `solve_merge`
Direct access to the MWIS discrete optimizer for pre-extracted symbol touch sets.
* **Input parameter:** `proposals_json` (stringified JSON array of proposals with `files` or `symbol_analysis` dictionaries and `weight` values).
* **Returns:**
  ```json
  {
    "status": "success",
    "accepted_proposals": ["p1", "p3"],
    "deferred_proposals": ["p2"],
    "total_nodes": 3,
    "total_conflict_edges": 1,
    "preservation_bound_guarantee": 0.5
  }
  ```

---

## Conflict Tiers Explained

GraphMerge classifies conflicts into two distinct AST tiers:

1. **Tier 1 (Syntactic Definition Collision):**
   * Two proposals modify the exact same function, method, or class scope in the same module.
   * *Example:* Agent 1 modifies `math_utils.py:calculate_ratio` and Agent 2 also modifies `math_utils.py:calculate_ratio`.
   * *Resolution:* Only the higher-gain proposal is accepted into current baseline $s_t$; the other is deferred to Cycle $t+1$.

2. **Tier 2 (Semantic Def-Use Call Graph Collision):**
   * Proposal A modifies the definition of symbol $S$ in `module_a.py`.
   * Proposal B adds or alters a call to symbol $S$ (or imports $S$) in `module_b.py`.
   * *Example:* Agent 1 alters signature `def calculate_tax(amount, rate, country_code)` in `tax.py`, while Agent 2 introduces call `calculate_tax(subtotal, 0.05)` in `checkout.py`.
   * *Resolution:* GraphMerge detects the def-use dependency and flags a Tier 2 collision, preventing a broken signature runtime crash.

---

## Client Configuration Reference

### Google Antigravity (AGY)
Configured in `~/.gemini/config/mcp_config.json`:
```json
{
  "mcpServers": {
    "graphmerge": {
      "command": "/Users/braj/graphmerge/.venv/bin/python3",
      "args": ["-m", "graphmerge.mcp_server"],
      "cwd": "/Users/braj/graphmerge",
      "description": "GraphMerge discrete block optimization & AST conflict arbitration for parallel AI coding agents (arXiv:2610.30074)",
      "enabled": true
    }
  }
}
```

### Claude Code
Add via CLI:
```bash
claude mcp add -s user graphmerge -- /Users/braj/graphmerge/.venv/bin/python3 -m graphmerge.mcp_server
```
Check health:
```bash
claude mcp list
# Displays: graphmerge: ... - ✔ Connected
```

### Cursor
Add to `.cursor/mcp.json` or `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "graphmerge": {
      "command": "python3",
      "args": ["-m", "graphmerge.mcp_server"],
      "cwd": "/path/to/graphmerge"
    }
  }
}
```

---

## Best Practices for Agents

1. **Always Pre-Check Diffs:** When running parallel subagents or preparing to merge two conflicting branches, call `check_patch_collision` before attempting `git merge` or `git apply`.
2. **Batch Multiple Diffs:** If 3 or more agents submit patches, pass all diffs in a single JSON payload to `arbitrate_diff_patches`.
3. **Respect Independent Set Output:** Apply only the patches returned in `accepted_patches`. Never force unselected patches into the same commit.
4. **Use Adaptive Feedback:** Take the deferred patches and use `generate_reprompt_instruction` to prompt the respective subagents to adapt their code against the newly committed baseline.
