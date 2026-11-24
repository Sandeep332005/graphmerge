# Contributing to GraphMerge

Thank you for your interest in contributing to **GraphMerge**! We welcome contributions from researchers, systems engineers, and open-source developers working on multi-agent collaboration, AST analysis, and discrete block optimization.

GraphMerge is the open-source reference implementation of [arXiv:2610.30074](https://arxiv.org/abs/2610.30074): *Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization*.

---

## 🛠️ Local Development Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Sandeep332005/graphmerge.git
cd graphmerge

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev,languages]"
```

### 2. Run Test Suites

Run the full unit test suite:
```bash
pytest tests/unit -v
```

Run MCP end-to-end integration tests:
```bash
python tests/mcp_e2e/run_e2e_tests.py
```

### 3. Verify Code Quality

We use [Ruff](https://github.com/astral-sh/ruff) for linting and code formatting:
```bash
ruff check .
ruff format --check .
```

---

## 🏗️ Architecture & Contribution Areas

1. **AST Analysis (`src/graphmerge/analysis/`)**:
   - Multi-language AST parsing via Tree-Sitter (Python, JavaScript, TypeScript, Go, Rust, Java).
   - Tier 1: Function, method, class, and struct scope overlap detection.
   - Tier 2: Cross-file Definition-Use (Def-Use) call graph and import collision analysis.

2. **Discrete Optimization (`src/graphmerge/optimization/`)**:
   - Maximum Weight Independent Set (MWIS) solver for conflict graph $G=(V, E)$.
   - Fractional chromatic bound $\frac{1}{\chi_f(G)}$ preservation computation.

3. **MCP Server & Tooling (`src/graphmerge/mcp_server.py`, `src/graphmerge/cli.py`)**:
   - Model Context Protocol tools (`arbitrate_diff_patches`, `check_patch_collision`, `solve_merge`, `generate_reprompt_instruction`).
   - Interactive CLI runner (`graphmerge demo`).

---

## 📝 Pull Request Guidelines

1. **Branch Naming**: Use descriptive prefixes like `feat/`, `fix/`, or `docs/` (e.g., `feat/cpp-ast-support`, `fix/tier2-builtin-filter`).
2. **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(ast): add C++ tree-sitter language parser`
   - `fix(optimizer): handle disconnected conflict graph edge cases`
   - `docs: update MCP client setup guide`
3. **Tests Required**: Every new feature or bugfix must include corresponding unit tests in `tests/unit/`.
4. **No Code Regressions**: Ensure all 74+ unit tests pass before submitting your PR.

---

## 💬 Community & Questions

- Report bugs or propose new features via [GitHub Issues](https://github.com/Sandeep332005/graphmerge/issues).
- Reference paper: [arXiv:2610.30074](https://arxiv.org/abs/2610.30074).
