# GraphMerge MCP E2E Test Plan

## Overview
This test plan defines rigorous validation criteria for the GraphMerge MCP server (`graphmerge.mcp_server`) across 9 specialized validation workers (W1-W9).

## Test Matrix & Pass Criteria

| Worker | Test Item | Pass Criterion | Failure Modes & Distinguishing Artifacts |
|--------|-----------|----------------|-------------------------------------------|
| **W1** | Handshake & Tool Discovery | `initialize` completes successfully; `tools/list` returns all 4 expected tools (`arbitrate_diff_patches`, `check_patch_collision`, `solve_merge`, `generate_reprompt_instruction`). | **Failure:** JSON-RPC timeout or missing tools. **Artifact vs Bug:** Check if server path is correct and venv is active. |
| **W2** | Happy Path (Valid Input) | Each of the 4 tools successfully processes valid JSON/diff inputs and returns `"status": "success"` with correct schema. | **Failure:** Python exception inside tool handler. **Artifact vs Bug:** Malformed test diff syntax vs Tree-Sitter parser error. |
| **W3** | Bad Input Handling | Malformed JSON, missing fields, or empty patch lists return error structures (`"status": "error"`) without crashing the server. | **Failure:** Server crashes (EOFError) on bad input instead of returning error JSON. **Artifact vs Bug:** Unhandled exception in core optimizer vs MCP protocol error. |
| **W4** | Conflict Graph Detection | Overlapping symbol modifications (`math.py:ratio`) produce a conflict edge (`total_conflict_edges > 0`), while disjoint modifications produce zero edges. | **Failure:** False positive/negative collision detection. **Artifact vs Bug:** Tree-Sitter AST scope parsing issue vs incorrect test diff hunk format. |
| **W5** | MWIS Arbitration & Optimality | Returned accepted patches form a valid independent set with total weight $\ge$ the naive greedy baseline. | **Failure:** Accepted set contains conflicting nodes. **Artifact vs Bug:** PuLP/NetworkX solver error vs incorrect weight assignment in test case. |
| **W6** | Determinism | Running the exact same arbitration input 3 consecutive times yields identical accepted/deferred sets and preservation bounds. | **Failure:** Non-deterministic output. **Artifact vs Bug:** Unordered dictionary/set iteration serialization differences. |
| **W7** | Concurrent Load on Single Server | Firing $N=10$ parallel async tool requests at a single shared server process completes without crashes, deadlocks, or cross-talk/mixed responses. | **Failure:** Corrupted JSON-RPC pipe or server crash under load. **Artifact vs Bug:** Stdio stream interleaving vs asyncio task cancellation. |
| **W8** | Lifecycle & Orphan Prevention | Spawning and terminating server processes properly cleans up PIDs; orphan check verifies zero lingering processes by PID. | **Failure:** Zombie or orphan processes remaining after test completion. **Artifact vs Bug:** Signal handling vs premature client disconnect. |
| **W9** | Independent Verification of Claims | Independently compute fractional coloring bound $1/\chi_f(G)$ and parallelism speedup from raw graph structures, matching or validating theoretical claims. | **Failure:** Computed bound differs from theoretical graph chromatic number. **Artifact vs Bug:** Fractional relaxation solver precision vs test graph definition. |
