# SERVER_SPEC.md — GraphMerge MCP Server Specification

## 1. Server Entrypoint & Launch Configuration
- **Entrypoint File:** `src/graphmerge/mcp_server.py`
- **Launch Command:** `python -m graphmerge.mcp_server` (or the `graphmerge-mcp` console script)
- **Virtual Environment:** Create with `python -m venv .venv && pip install -e ".[dev]"`
- **Transport Mechanism:** Standard Input / Output (`stdio`) via the official Model Context Protocol (MCP) Python SDK (`mcp.server.mcpserver.MCPServer` or `mcp.server.fastmcp.FastMCP`).

---

## 2. Inventory of Exposed Tools & Schemas

The server exposes 4 MCP tools:

### 1. `arbitrate_diff_patches`
- **Description:** Takes a JSON array of diff patches, runs Tree-Sitter AST extraction and two-tier conflict detection, and returns the certified independent set $\mathcal{I}^*$.
- **Parameters:**
  - `diffs_json` (string, required): JSON stringified array of patch objects:
    ```json
    [
      {
        "id": "string",
        "task_id": "string (optional)",
        "diff": "string (unified diff)",
        "weight": "float (optional)"
      }
    ]
    ```
- **Return Type:** JSON string containing `status`, `accepted_patches`, `deferred_patches`, `syntax_rejected_patches`, `total_patches_evaluated`, `total_conflict_edges`, `conflict_diagnostics`, and `preservation_bound`.

### 2. `check_patch_collision`
- **Description:** Compares two candidate unified diffs and checks for syntactic or def-use collisions.
- **Parameters:**
  - `diff_a` (string, required): Unified diff of patch A.
  - `diff_b` (string, required): Unified diff of patch B.
  - `id_a` (string, optional, default: `"patch_a"`): Identifier for patch A.
  - `id_b` (string, optional, default: `"patch_b"`): Identifier for patch B.
- **Return Type:** JSON string containing `has_conflict`, `can_merge_concurrently`, `conflict_type`, `tier`, `symbol`, and `details`.

### 3. `solve_merge`
- **Description:** Solves discrete MWIS for pre-extracted symbol touch sets and weights.
- **Parameters:**
  - `proposals_json` (string, required): JSON stringified array of proposal objects with `files` or `symbol_analysis` and `weight`.
- **Return Type:** JSON string containing `status`, `accepted_proposals`, `deferred_proposals`, `total_nodes`, `total_conflict_edges`, and `preservation_bound_guarantee`.

### 4. `generate_reprompt_instruction`
- **Description:** Generates adaptive re-prompt instructions for LLM worker agents whose patches were deferred due to collisions.
- **Parameters:**
  - `task_id` (string, required): Task identifier.
  - `colliding_patch_ids` (string, required): Comma-separated list of colliding accepted patch IDs.
  - `colliding_symbols` (string, required): Comma-separated list of colliding symbol names.
  - `baseline_version` (string, optional, default: `"s_1"`): Target baseline version.
- **Return Type:** JSON string containing `task_id`, `target_baseline`, and `instruction`.

---

## 3. Environment & Configuration
- **Required Environment Variables:** None (`os.environ` is not utilized for core operation).
- **API Keys / External Services:** None (fully local execution using Python, NetworkX, PuLP, and Tree-Sitter).
- **Configuration Files:**
  - Project-level: `.mcp.json` in the repository root
  - Claude Code: `claude mcp add graphmerge -- python -m graphmerge.mcp_server`
  - Antigravity / Cursor: see README for per-client setup
