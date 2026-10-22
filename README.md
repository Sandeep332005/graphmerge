# GraphMerge ⚡
### Parallel AI Agent Collaboration via Graph-Structured Distributed Block Optimization

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/arXiv-2610.30074-b31b1b.svg)](https://arxiv.org/abs/2610.30074)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-green.svg)](https://modelcontextprotocol.io/)

> **The world's first open-source reference implementation of *Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization* ([arXiv:2610.30074](https://arxiv.org/abs/2610.30074), October 2026).**

---

## 📌 The Problem: The "Merge Degradation" Paradox

When multiple autonomous coding agents (Devin, SWE-agent, AutoGen, CrewAI) operate concurrently on a shared codebase, their independently verified code patches frequently conflict:
* **Syntactic Conflicts:** Overlapping diffs breaking standard `git merge`.
* **Semantic Regressions:** Breaking shared function signatures, call graphs, or global state.

Current industry solutions either **force agents into an $O(N)$ sequential queue** (painfully slow) or use an **LLM judge** to merge code (stochastic, hallucinations, and code loss).

## 💡 The Solution: Graph-Structured Block Optimization

GraphMerge models parallel multi-agent code integration as **Discrete Block Optimization on a Symbol Conflict Graph $G=(V, E)$**:

1. **Nodes ($V$):** Each proposed agent diff $p_i$.
2. **Edges ($E$):** Semantic AST symbol collisions detected via **Tree-Sitter**.
3. **Independent Sets ($\mathcal{I}^* \subseteq V$):** Certified conflict-free patch combinations.
4. **Theoretical Guarantee:** Proved in *arXiv:2610.30074*, an optimal fractional coloring preserves at least a **$\frac{1}{\chi_f(G)}$ fraction** of verified local improvement.
5. **Geometric Convergence:** Conflicted patches are staged, rebased, and resolved in successive iterations, achieving provably optimal code synthesis.

---

## 🏗️ System Architecture

```
flowchart TD
    A["Input Task Backlog<br/>T1, T2, T3"] --> B["Git Working Baseline: s_0"]

    subgraph W["Worker Agents Processing"]
        direction LR
        P1["Worker Agent 1<br/>Diff Patch p1"]
        P2["Worker Agent 2<br/>Diff Patch p2"]
        P3["Worker Agent 3<br/>Diff Patch p3"]
    end

    B --> P1
    B --> P2
    B --> P3

    subgraph S["Semantic Conflict Analysis"]
        C["Tree-sitter AST Conflict Extractor<br/>Functions, Classes, Scopes, Imports"]
        G["NetworkX Conflict Graph<br/>G = V, E"]
        M["Maximum Weight Independent Set (MWIS)<br/>Solver: Exact Complement Clique / Fractional LP"]
        C --> G --> M
    end

    P1 --> C
    P2 --> C
    P3 --> C

    subgraph R["Resolution & Validation"]
        direction LR
        I["Certified Independent Set<br/>e.g. p1, p3"]
        T["Docker Sandbox Test Runner<br/>Pytest Execution"]
        X["Staged Conflicted Edits<br/>e.g. p2"]
        I --> T
    end

    M --> I
    M --> X

    subgraph E["Baseline Evolution"]
        N["Commit I* to New Baseline s_1"]
        D{"Convergence Check:<br/>Remaining Tasks?"}
        NEXT["Cycle 2 / Next Iteration"]
        N --> D
        D -->|Yes| NEXT
    end

    T --> N
    X --> N
    D -->|No| DONE(("Process Complete"))

    classDef input fill:#ed8bea,stroke:#333,color:#222;
    classDef solver fill:#aaa8f5,stroke:#333,color:#222;
    classDef test fill:#c9f4c9,stroke:#333,color:#222;
    classDef commit fill:#fffbd0,stroke:#333,color:#222;
    classDef decision fill:#ffb2b2,stroke:#333,color:#222;

    class A input;
    class M solver;
    class T test;
    class N commit;
    class D decision;

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/graphmerge/graphmerge.git
cd graphmerge
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 2. Basic Python API
```python
from graphmerge.optimization.solver import ConflictGraphOptimizer

# 1. Initialize optimizer
optimizer = ConflictGraphOptimizer()

# 2. Define proposals with touched AST symbols and local gain scores
proposals = [
    {"id": "p1", "files": {"math_utils.py": {"calculate_ratio"}}, "weight": 10.0},
    {"id": "p2", "files": {"math_utils.py": {"calculate_ratio"}}, "weight": 8.0},  # Collides with p1
    {"id": "p3", "files": {"formatters.py": {"format_iso"}}, "weight": 12.0}       # Independent
]

# 3. Build graph & solve Maximum Weight Independent Set
optimizer.build_conflict_graph(proposals)
accepted, rejected = optimizer.solve_mwis()

print("Certified Compatible Merges:", accepted)  # {'p1', 'p3'}
print("Deferred for Round 2 Rebase:", rejected)  # {'p2'}
```

### 3. Model Context Protocol (MCP) Server
Launch the MCP server to integrate directly with **Cursor**, **Claude Code**, or **Nimbalyst**:
```bash
python -m graphmerge.mcp_server
```

---

## 📊 Comprehensive Deliverables & Documentation

* 📄 **[Full Academic Pre-Development Report (PDF)](docs/project_report_graphmerge.pdf)**: 20-page formal specification with literature review, formal math model, and test matrix.
* 📝 **[Full Academic Pre-Development Report (Markdown)](docs/project_report_graphmerge.md)**: Markdown version with all 17 chapters.
* 🎨 **[Interactive Architecture Canvas (Excalidraw)](docs/graphmerge_architecture.flowchart.excalidraw)**: 6-layer vector visual flow (open in [excalidraw.com](https://excalidraw.com) or Nimbalyst).

---

## 📑 Citation

If you use GraphMerge in your research or reference this discrete block optimization implementation, please cite:

```bibtex
@article{graphmerge2026,
  title={GraphMerge: Parallel AI Agent Collaboration via Graph-Structured Distributed Block Optimization},
  author={GraphMerge Contributors},
  journal={GitHub Repository},
  year={2026},
  url={https://github.com/graphmerge/graphmerge},
  note={Reference implementation of arXiv:2610.30074}
}
```

```bibtex
@article{li2026parallel,
  title={Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization},
  author={Li, Hanmin and others},
  journal={arXiv preprint arXiv:2610.30074},
  year={2026}
}
```

---

## 📜 License
This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details. Includes patent and copyright grants for open-source research.
