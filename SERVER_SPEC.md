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

---

## 4. Interactive Browser Verification (MCP Inspector)
The server can be interactively tested without configuring a client using the official MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python3 -m graphmerge.mcp_server
```
This serves a local web testing harness (typically at `http://localhost:5173`) allowing real-time execution of all 4 tools with live JSON-RPC input/output inspection.

---

## 5. Multi-Language Tree-Sitter AST Engine
GraphMerge supports multi-language syntax validation and AST symbol extraction:
- **Python**: `tree-sitter-python` (with fallback to standard library `ast`)
- **JavaScript & TypeScript**: `tree-sitter-javascript`, `tree-sitter-typescript`
- **Go**: `tree-sitter-go`
- **Rust**: `tree-sitter-rust`
- **Java**: `tree-sitter-java`

Two tiers of AST conflict analysis are performed:
1. **Tier 1 (Syntactic Collision)**: Identifies whether two candidate patches mutate overlapping function, method, or class AST definition scopes.
2. **Tier 2 (Semantic Def-Use Collision)**: Traces whether one patch alters a function/method signature that another patch invokes or imports.

---

## 6. CLI & Interactive Terminal Demo
GraphMerge provides zero-argument interactive terminal evaluation:
```bash
graphmerge demo
# or
python3 -m graphmerge.cli demo
```
Options:
- `--json`: Outputs raw JSON results rather than the ANSI-formatted terminal dashboard.

---

## 7. Performance & Theoretical Guarantees
- **Theoretical Bound**: Proved in *arXiv:2610.30074*, fractional coloring guarantees preservation of at least a $\frac{1}{\chi_f(G)}$ fraction of verified local improvement.
- **Benchmark Suite**: Run `python benchmarks/mwis_benchmark.py` to evaluate solver latency and gain preservation scaling across 5 to 100 concurrent agent proposals. Sub-millisecond arbitration latency is achieved across all standard graph scales.
