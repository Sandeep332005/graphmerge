# GraphMerge: Parallel AI Agent Collaboration via Graph-Structured Distributed Block Optimization
## Comprehensive Pre-Development Engineering & Research Report

---

### Project Metadata
* **Project Title:** GraphMerge: Parallel AI Agent Collaboration via Graph-Structured Distributed Block Optimization
* **Document Version:** 1.0.0 (Pre-Implementation Baseline)
* **Status:** Planning & Architectural Specification (No code has been implemented)
* **Domain:** AI Systems / Software Engineering / Multi-Agent Systems
* **Target Audience:** University Evaluator / Academic Project Advisor / Senior Systems Architect
* **Primary Reference:** *Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization*, arXiv:2610.30074 (`cs.AI`, October 2026)
* **Estimated Execution Timeline:** 4 to 6 Weeks (Undergraduate / Graduate Capstone or Research Project)

---

## Table of Contents
1. [Chapter 1 — Executive Summary](#chapter-1--executive-summary)
2. [Chapter 2 — Problem Definition](#chapter-2--problem-definition)
3. [Chapter 3 — Literature Review and Existing Solutions](#chapter-3--literature-review-and-existing-solutions)
4. [Chapter 4 — Proposed Solution and Novelty](#chapter-4--proposed-solution-and-novelty)
5. [Chapter 5 — System Architecture](#chapter-5--system-architecture)
6. [Chapter 6 — End-to-End System Workflow](#chapter-6--end-to-end-system-workflow)
7. [Chapter 7 — Technology Stack and Justification](#chapter-7--technology-stack-and-justification)
8. [Chapter 8 — Algorithms and Technical Foundations](#chapter-8--algorithms-and-technical-foundations)
9. [Chapter 9 — Data, Interfaces, and Schemas](#chapter-9--data-interfaces-and-schemas)
10. [Chapter 10 — Implementation Roadmap](#chapter-10--implementation-roadmap)
11. [Chapter 11 — Testing and Verification Strategy](#chapter-11--testing-and-verification-strategy)
12. [Chapter 12 — Evaluation and Benchmarking Plan](#chapter-12--evaluation-and-benchmarking-plan)
13. [Chapter 13 — Risk Analysis](#chapter-13--risk-analysis)
14. [Chapter 14 — Resource and Cost Estimation](#chapter-14--resource-and-cost-estimation)
15. [Chapter 15 — Expected Results and Limitations](#chapter-15--expected-results-and-limitations)
16. [Chapter 16 — Project Deliverables and Repository Layout](#chapter-16--project-deliverables-and-repository-layout)
17. [Chapter 17 — Conclusion and Go/No-Go Decision](#chapter-17--conclusion-and-gono-go-decision)
18. [References](#references)
19. [Checklist: Before Writing the First Line of Code](#checklist-before-writing-the-first-line-of-code)

---

## Chapter 1 — Executive Summary

### 1.1 Project Overview
Modern autonomous coding and problem-solving agents (e.g., SWE-agent, Devin-style pipelines) operate almost exclusively in a **single-agent, sequential execution loop**. When multiple AI agents are launched concurrently to solve sub-tasks across a codebase, their proposed modifications frequently conflict. Combining these proposals naively degrades or breaks the shared code solution.

**GraphMerge** is an open-source, mathematically grounded coordination harness built on **LangGraph**, **NetworkX**, and **Tree-Sitter**. It translates the theoretical breakthroughs of recent research (*arXiv:2610.30074*) into an operational system. Instead of relying on stochastic LLM prompts to "merge" conflicting agent code or forcing agents into a slow $O(N)$ sequential queue, GraphMerge models parallel agent collaboration as **Discrete Block Optimization over an AST/Symbol Dependency Graph $G=(V, E)$**.

### 1.2 Problem Being Addressed
When $K$ parallel AI agents each produce an independently verified edit on a shared repository, merging their outputs creates two fatal failure modes:
1. **Syntactic Conflicts:** Overlapping file edits that standard version control tools (like `git merge`) cannot reconcile without human intervention.
2. **Semantic Regressions:** Non-overlapping text edits that silently break shared invariants (e.g., Agent 1 renames a function signature in module `A.py`, while Agent 2 introduces a caller to the old signature in module `B.py`).

Existing multi-agent frameworks (CrewAI, AutoGen, vanilla LangGraph) either avoid parallelism entirely or prompt an "LLM Judge" to merge diffs, which introduces hallucinations, high token costs, and zero deterministic guarantees.

### 1.3 Proposed Solution
GraphMerge constructs an undirected dependency graph $G=(V,E)$ where nodes $V$ represent proposed agent patches and edges $E$ represent semantic and syntactic collisions identified via Abstract Syntax Tree (AST) analysis. By computing a **Maximum Weight Independent Set (MWIS)** and leveraging **fractional chromatic graph coloring**, the system deterministically selects a maximal subset of mutually compatible edits that guarantees zero conflict collisions and preserves at least a $\frac{1}{\chi_f(G)}$ fraction of verified local improvement. Conflicting edits are not dropped; they are rebased and rolled forward into subsequent iterations, guaranteeing geometric convergence toward an optimal codebase state.

### 1.4 Expected Contribution
1. **First Reference Implementation:** The first public, open-source reference implementation of the theoretical framework introduced in *arXiv:2610.30074*.
2. **Production-Ready LangGraph Harness:** A plug-and-play orchestration harness capable of dispatching $K$ parallel agents and deterministically merging their outputs.
3. **Rigorous Empirical Benchmark:** A reproducible comparative benchmark against sequential ReAct agents, naive Git 3-way merges, and LLM-judge synthesizers across synthetic and open-source multi-file Python repositories.

### 1.5 Intended Users
* **AI & Software Engineering Researchers:** Investigating multi-agent coordination dynamics, game theory, and distributed code synthesis.
* **Autonomous Engineering Tool Developers:** Teams building automated bug-fixing bots, automated code review assistants, and continuous refactoring bots.
* **Academic Evaluators / University Committees:** Seeking mathematically grounded applications of discrete algorithms in modern generative AI systems.

### 1.6 Major Deliverables
* Complete Python package (`graphmerge`) with LangGraph state orchestration.
* Static AST conflict analysis engine utilizing Tree-Sitter.
* Discrete graph optimization engine utilizing NetworkX and linear programming relaxations.
* Isolated Dockerized sandboxing pipeline for deterministic patch testing.
* Automated benchmarking harness with reproducible metrics logging.
* Academic project report and reproducible demonstration suite.

### 1.7 Limitations of Scope
GraphMerge addresses *conflict detection, scheduling, and deterministic integration* of proposed edits. It does not replace the underlying LLM's capacity to generate correct code for an isolated subproblem, nor does it resolve semantic runtime bugs that are undetectable via static AST call graphs and unit test suites.

---

## Chapter 2 — Problem Definition

### 2.1 Background and Motivation
Large Language Model (LLM) agents have demonstrated substantial aptitude in isolated coding benchmarks such as SWE-bench. However, real-world software engineering requires processing large backlogs: refactoring multiple modules, patching several independent CVEs, and writing integration tests. 

Executing these tasks sequentially causes linear latency growth:
$$T_{\text{sequential}} = \sum_{i=1}^K t_i \approx K \cdot \bar{t}$$
Running agents concurrently could theoretically reduce wall-clock completion time to:
$$T_{\text{parallel}} = \max_{i \in \{1,\dots,K\}} t_i + t_{\text{merge}}$$
However, without formal coordination, $t_{\text{merge}}$ results in build breakages, semantic regression, or severe degradation of the shared codebase objective.

```
Problem-to-Solution Overview:

[ K Independent Tasks ]
         |
         v
+-----------------------------------------------------------+
| EXISTING STATE OF THE ART:                                |
| 1. Sequential Queue: O(K) wall time (extremely slow).     |
| 2. Naive Parallel + LLM Judge: Hallucinates, drops code.   |
| 3. Standard Git 3-Way Merge: Fails on non-textual conflicts|
+-----------------------------------------------------------+
         |
         | (GraphMerge Paradigm)
         v
+-----------------------------------------------------------+
| PROPOSED SOLUTION (arXiv:2610.30074):                     |
| 1. Parallel Agent Fan-Out: Run in O(1) concurrent time.    |
| 2. Static AST Dependency Extraction: Build Graph G=(V,E). |
| 3. Discrete Block Optimization: Solve Maximum Ind. Set.   |
| 4. 1/χ_f(G) Guaranteed Conflict-Free Integration.         |
| 5. Rebase & Iterate: Geometric convergence to goal.       |
+-----------------------------------------------------------+
```

### 2.2 Formal Problem Statement
Let $\mathcal{S}$ denote the state space of a software repository, and let $s_0 \in \mathcal{S}$ be the baseline state. Let $f: \mathcal{S} \to \mathbb{R}_{\ge 0}$ be a monotonic objective evaluation function (e.g., number of passing unit tests minus linting penalties, or formal test pass score).

Let $\{A_1, A_2, \dots, A_K\}$ be $K$ parallel agents, where each agent $A_i$ proposes an edit (patch) $p_i$ that transforms $s_0$ to $s_i = s_0 \oplus p_i$. Each proposal provides a verified local improvement:
$$\Delta f_i = f(s_0 \oplus p_i) - f(s_0) > 0$$

When a subset of edits $S \subseteq \{p_1, \dots, p_K\}$ is applied simultaneously, the resulting state is $s_S = s_0 \bigoplus_{p \in S} p$. In the presence of interactions, the combined gain does not equal the sum of local gains:
$$\Delta f(S) = f(s_S) - f(s_0) \ne \sum_{p_i \in S} \Delta f_i$$

**The Optimization Goal:** Identify a conflict graph $G = (V, E)$ where $V = \{p_1, \dots, p_K\}$ and an edge $(p_i, p_j) \in E$ indicates an incompatible interaction. Find an independent set $\mathcal{I}^* \subseteq V$ such that:
$$\mathcal{I}^* = \arg\max_{\mathcal{I} \in \text{Ind}(G)} \sum_{p_i \in \mathcal{I}} w_i$$
where $w_i = \Delta f_i$, subject to the guarantee that for all $p_i, p_j \in \mathcal{I}^*$, no syntactic or semantic AST dependencies are violated.

### 2.3 Requirements Specification

#### 2.3.1 Functional Requirements (FR)
* **FR-01 (Parallel Dispatch):** The system must concurrently dispatch up to $K$ configurable worker agents over an isolated workspace branch using LangGraph.
* **FR-02 (Structured Diff Capture):** The system must capture agent outputs as standardized, verifiable unified diffs with metadata detailing targeted files, modified line ranges, and modified AST identifiers.
* **FR-03 (AST Dependency Analysis):** The system must parse target source files using Tree-Sitter to identify function, class, variable, and import scopes touched by each patch.
* **FR-04 (Conflict Graph Generation):** The system must construct an undirected graph $G=(V, E)$ where an edge $(u, v)$ is added if patch $u$ and patch $v$ share overlapping AST symbol scopes, line ranges, or import dependencies.
* **FR-05 (Discrete Optimization Solver):** The system must solve the Maximum Weight Independent Set (MWIS) over $G$ using exact branch-and-bound for $|V| \le 20$ and fractional linear programming relaxations for $|V| > 20$.
* **FR-06 (Sandboxed Verification):** The system must apply the chosen independent set of patches in an isolated Docker container and execute verification tests (`pytest`).
* **FR-07 (Rebase and Convergence Loop):** The system must rebase unselected/rejected patches onto the newly updated base state and schedule them for subsequent optimization rounds.

#### 2.3.2 Non-Functional Requirements (NFR)
* **NFR-01 (Determinism):** For a static set of proposals and baseline state, the graph construction and MWIS solver must produce identical output across repeated runs.
* **NFR-02 (Optimizer Latency):** Conflict graph construction and optimization for $K \le 20$ proposals must execute in under 2.0 seconds (excluding containerized test run time).
* **NFR-03 (Isolation & Safety):** Code evaluation must occur within restricted Docker containers without host network access or root volume mount privileges.
* **NFR-04 (Auditability):** Every merge decision, graph adjacency matrix, and intermediate verification log must be persisted as structured JSON artifacts.

### 2.4 Scope and Exclusions
* **In Scope:** Python codebases, static AST parsing, unit-test-based objective verification, single-repository multi-file modifications, LangGraph-based workflow orchestration.
* **Out of Scope:** Dynamic runtime tracing of uncalled functions, polyglot repositories (non-Python languages deferred to v2), automated repair of fundamentally flawed individual agent logic.

### 2.5 Research Questions and Hypotheses
* **RQ1:** Does graph-structured discrete block optimization achieve a statistically significant higher Merge Success Rate (MSR) than naive Git 3-way merges and LLM-judge arbiters?
  * *Hypothesis 1:* GraphMerge will achieve $\ge 95\%$ build/test pass rate on merged sets, whereas naive Git will fail on $\ge 40\%$ of semantically coupled tasks.
* **RQ2:** What is the empirical wall-clock speedup factor ($S_p$) of parallel agent execution coordinated by GraphMerge compared to sequential execution?
  * *Hypothesis 2:* GraphMerge will achieve an empirical speedup of $S_p \ge 2.5\times$ for $K=5$ concurrent agents while maintaining equivalent solution quality.
* **RQ3:** Does the theoretical $1/\chi_f(G)$ bound hold empirically as a lower bound for preserved objective gains across multi-task benchmarks?

---

## Chapter 3 — Literature Review and Existing Solutions

### 3.1 Review of Primary Literature

#### 1. *Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization*
* **Authors / Identifier:** Anonymous / Preprint, arXiv:2610.30074 (`cs.AI`, Oct 22, 2026).
* **Core Contribution:** Formulates parallel agent coordination as discrete block optimization. Introduces the theoretical guarantee that fractional graph coloring yields an edit merger preserving at least a $\frac{1}{\chi_f(G)}$ fraction of verified local improvement. Proves geometric convergence under block error-bound conditions.
* **Limitation:** Focuses on theoretical formulation, synthetic graphs, and high-level experiments; does not provide an open-source, production-ready framework integrated into modern agent orchestration graphs (e.g., LangGraph).
* **Direct Relevance:** Primary theoretical foundation for this project.

#### 2. *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*
* **Authors / Identifier:** John Yang, Carlos E. Jimenez, Alexander Wettig, et al., arXiv:2405.15793 (2024).
* **Core Contribution:** Establishes the Agent-Computer Interface (ACI), proving that giving LLMs specialized, shell-like commands to view, edit, and navigate code dramatically improves software repair benchmark scores.
* **Limitation:** Purely single-agent sequential architecture. Does not support concurrent multi-agent branches or parallel merge strategies.
* **Direct Relevance:** Serves as the design blueprint for our worker agent prompt-action interface.

#### 3. *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation*
* **Authors / Identifier:** Qingyun Wu, Gagan Bansal, Jieyu Zhang, et al., arXiv:2308.08155 (2023).
* **Core Contribution:** Demonstrates multi-agent conversation patterns, role-playing, and cooperative task solving.
* **Limitation:** Coordination is predominantly discursive (agents chatting in natural language). When conflicts occur in code generation, AutoGen relies on human intervention or conversation summarization, lacking discrete mathematical merge guarantees.
* **Direct Relevance:** Represents the current state of conversational multi-agent systems that GraphMerge aims to outperform in deterministic code synthesis.

#### 4. *Semantic Merge Conflict Detection in Component-Based Software Systems*
* **Authors / Identifier:** S. Leßenich, S. Apel, and C. Kästner, *IEEE Transactions on Software Engineering*, 2018.
* **Core Contribution:** Analyzes why structured and semistructured merge tools outperform unstructured (line-based) Git merges by parsing AST trees.
* **Limitation:** Classical software engineering paper pre-dating generative AI agents; assumes human developers with structured branch lifecycles, not high-frequency autonomous agent patch generation.
* **Direct Relevance:** Provides the formal justification for AST-level symbol dependency checking instead of lexical line diffing.

### 3.2 Comparison of Existing Solutions

| System / Approach | Concurrency Model | Conflict Resolution Mechanism | Determinism Guarantee | Semantic Dependency Awareness | Cost Efficiency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sequential ReAct (SWE-agent)** | Strictly Sequential $O(K)$ | N/A (One task at a time) | High | High (Context carried sequentially) | Moderate (High wall time) |
| **Naive Git 3-Way Merge** | Fully Parallel $O(1)$ | Line-level text matching | High | **Zero** (Blind to syntax & AST) | High (Zero token cost, high failure rate) |
| **LLM-Judge / Synthesizer** | Fully Parallel $O(1)$ | Prompt-based LLM arbitration | **Very Low (Stochastic)** | Medium (Subject to hallucination) | Very Low (High extra token spend) |
| **AutoGen / CrewAI** | Conversational / Turn-based | Natural language debate / Human loop | Low | Low | Low (Chat token overhead) |
| **GraphMerge (Proposed)** | **Graph-Optimized Parallel** | **Discrete Block Optimization (MWIS)** | **Provably Deterministic** | **High (Tree-Sitter AST Scope)** | **High (Optimal compute-cost tradeoff)** |

### 3.3 Research Gap
Current multi-agent frameworks operate on two extremes: either **safe but painfully slow sequential queues**, or **fast but brittle parallel runs reconciled by stochastic LLM summarizers**. There is an absolute void of systems that employ **discrete mathematical optimization and static AST analysis** to govern agent output integration. GraphMerge bridges this gap.

---

## Chapter 4 — Proposed Solution and Novelty

### 4.1 Proposed Approach
GraphMerge introduces an agent coordination architecture based on three tenets:
1. **Isolated Parallel Execution:** $K$ sub-agents generate patches concurrently in decoupled virtual workspaces without cross-agent chatter.
2. **Deterministic Conflict Extraction:** A static AST parser ingests diffs, maps changes to symbol nodes in the codebase AST, and produces a mathematically rigorous conflict graph $G=(V, E)$.
3. **Discrete Optimization Selection:** A graph solver selects the Maximum Weight Independent Set $\mathcal{I}^*$, applying only mathematically certified compatible patches in Round 1, while staging conflicting edits for rebase in Round 2.

```
+-------------------------------------------------------------+
|                     GraphMerge Pipeline                     |
|                                                             |
|  [Parallel LLM Workers] ---> Raw Diffs & Touch Sets         |
|                                    |                        |
|                                    v                        |
|  [Tree-Sitter AST Parser] -> Symbol Interaction Graph       |
|                                    |                        |
|                                    v                        |
|  [NetworkX MWIS Solver]  --> Optimal Independent Set I*     |
|                                    |                        |
|                                    v                        |
|  [Docker Test Sandbox]   --> Verified Merged Commit         |
|                                    |                        |
|                                    v                        |
|  [Rebase Engine]         --> Leftover Edits -> Round 2      |
+-------------------------------------------------------------+
```

### 4.2 Minimum Viable Product (MVP) vs. Future Scope

#### Included in MVP (Scope of this Project)
* Support for Python 3.10+ target repositories.
* Tree-Sitter AST dependency extractor for functions, classes, and global variables.
* LangGraph state machine orchestrating 3 to 5 parallel workers.
* Exact Maximum Weight Independent Set solver using NetworkX for small graphs ($|V| \le 20$).
* Docker-based sandboxed patch application and `pytest` execution.
* Comprehensive benchmarking suite against Sequential ReAct and Naive Git Merge baselines.

#### Deferred to Future Versions (v2.0+)
* Polyglot support (TypeScript, Rust, Go AST extractors).
* Dynamic taint tracking and runtime call-graph instrumentation.
* Distributed multi-node worker clusters across cloud infrastructure.
* Integration with GitHub Actions PR automation.

---

## Chapter 5 — System Architecture

### 5.1 High-Level Architecture

```mermaid
flowchart TD
    subgraph UserInterface ["1. Input and Dispatch Layer"]
        CLI["CLI / Task Dispatcher"]
        Repo["Target Codebase Repository Baseline s_0"]
    end

    subgraph LangGraphEngine ["2. LangGraph Hardened Orchestration Engine"]
        Supervisor["Supervisor Node"]
        W1["Worker Agent 1"]
        W2["Worker Agent 2"]
        W3["Worker Agent 3"]
        PreVerif["Worker Local Pre-Verification Node (Delta f_i > 0)"]
        AdaptiveReprompt["Adaptive Agent Re-Prompting Node (Collision Context)"]
        State["GraphMerge State Management"]
    end

    subgraph ConflictEngine ["3. Two-Tier Conflict and Optimization Layer"]
        AST["Two-Tier AST & Def-Use Extractor (Tier 1 Syntactic + Tier 2 Semantic)"]
        GraphBuilder["Linear Inverted Index Graph Builder G=(V,E)"]
        Optimizer["Divide-and-Conquer MWIS Solver"]
    end

    subgraph SandboxLayer ["4. Sandboxing and Verification Layer"]
        DockerMgr["Docker Container Manager"]
        PatchApp["Patch Application Engine"]
        TestRunner["Pytest Test Harness"]
        AtomicCommit["Atomic Baseline Commit (s_0 -> s_1)"]
    end

    subgraph StorageLayer ["5. Persistence and Artifact Layer"]
        Logs["JSON Traces and Evaluation Logs"]
        GitRepo["Git Workspace Manager"]
    end

    CLI --> Supervisor
    Repo --> State
    Supervisor -->|Fan-Out Task 1| W1
    Supervisor -->|Fan-Out Task 2| W2
    Supervisor -->|Fan-Out Task 3| W3
    W1 --> PreVerif
    W2 --> PreVerif
    W3 --> PreVerif
    PreVerif -->|Verified Proposals Delta f_i > 0| State
    State --> AST
    AST --> GraphBuilder
    GraphBuilder --> Optimizer
    Optimizer -->|Certified Independent Set I*| PatchApp
    Optimizer -->|Deferred Conflicted Patches| AdaptiveReprompt
    PatchApp --> DockerMgr
    DockerMgr --> TestRunner
    TestRunner -->|Pass/Fail Evidence| AtomicCommit
    AtomicCommit -->|New Baseline s_1| State
    State -->|Update Baseline| AdaptiveReprompt
    AdaptiveReprompt -->|Re-Prompt with Collision Context & s_1 Diffs| W2
    AtomicCommit --> GitRepo
    State --> Logs
```

### 5.2 Detailed Component Responsibilities

#### 1. Supervisor & State Orchestrator (`graphmerge.orchestration.supervisor`)
* **Purpose:** Manages the lifecycle of the optimization cycle, worker fan-out, and convergence checks.
* **Inputs:** Task definitions, baseline Git commit SHA, workspace path.
* **Outputs:** State updates, accepted patch lists, termination signals.
* **Communication:** Dispatches tasks to workers via LangGraph `Send` API; triggers downstream optimization nodes.

#### 2. Worker Local Pre-Verification Node (`worker_preverification_node`)
* **Purpose:** Validates each candidate patch locally ($s_t \oplus p_i$) before the coordinator admits it into the conflict graph.
* **Validation Rules:**
  1. *AST Syntax Validation:* Verifies whether the patch or diff hunks parse without syntax errors using `validate_diff_syntax`.
  2. *Empirical Gain Check:* Mandates empirical gain $\Delta f_i > 0$. Unverified or regressive patches ($\Delta f_i \le 0$) are moved to `rejected_unverified_patches` to prevent corrupting baseline $s_{t+1}$.

#### 3. Two-Tier AST & Def-Use Conflict Extractor (`graphmerge.analysis.ast_parser`)
* **Purpose:** Inspects each proposal against the baseline codebase AST to identify syntactic definition collisions and cross-file semantic call collisions.
* **Conflict Tiers:**
  * **Tier 1 (Syntactic Scope Collisions):** Multiple proposals modify the same function, class, or method body in the same module.
  * **Tier 2 (Semantic Def-Use Collisions):** Proposal $A$ modifies the definition of symbol $S$ in file $F_1$, and Proposal $B$ invokes or imports symbol $S$ in file $F_2$.
* **Outputs:** Structured `SymbolAnalysis` (definitions, calls, imports) and typed conflict edges.

#### 4. Adaptive Agent Re-Prompting Node (`adaptive_reprompt_node`)
* **Purpose:** Replaces naive/blind `git rebase` or `git apply` with a context-rich LLM agent re-prompt loop.
* **Mechanism:**
  * When Proposal $p_j$ is deferred due to conflict edges with accepted set $I^*$:
  * Constructs a **Collision Diagnostic Context** containing the colliding proposal IDs, exact colliding symbols, and the diff contents of the accepted $I^*$ patches.
  * Re-prompts the worker agent: *"Your patch for task $T_j$ conflicted with patches committed into baseline $s_{t+1}$. The target symbols have been updated. Regenerate your patch grounded in $s_{t+1}$."*
  * Worker produces an adapted patch $p_j'$ ready for clean integration in the next iteration.

#### 4. Conflict Graph Builder (`graphmerge.optimization.graph_builder`)
* **Purpose:** Constructs the undirected interaction graph $G = (V, E)$.
* **Inputs:** List of proposals and their corresponding `TouchSet` instances.
* **Outputs:** NetworkX `Graph` object with node weights and conflict edges.

#### 5. Discrete Optimizer (`graphmerge.optimization.solver`)
* **Purpose:** Solves the Maximum Weight Independent Set problem to select the optimal compatible patch set.
* **Inputs:** NetworkX graph $G=(V, E)$.
* **Outputs:** Certified list of patch IDs $\mathcal{I}^* \subseteq V$.

#### 6. Docker Sandboxed Evaluator (`graphmerge.sandbox.docker_runner`)
* **Purpose:** Applies candidate patches in a clean, ephemeral Docker container and runs regression test suites.
* **Inputs:** Baseline repository mount, patch set $\mathcal{I}^*$.
* **Outputs:** Exit code, stdout/stderr, test pass/fail counts.

---

## Chapter 6 — End-to-End System Workflow

### 6.1 End-to-End System Workflow Architecture

```mermaid
flowchart TD
    Start([User Submits Task Backlog]) --> InitBranch[Git: Create Working Branch s_0]
    
    subgraph FanOut [Parallel Agent Execution]
        InitBranch --> W1[Worker Agent 1: Task 1]
        InitBranch --> W2[Worker Agent 2: Task 2]
        InitBranch --> W3[Worker Agent 3: Task 3]
    end

    W1 --> Collect[Collect Proposals: Diff 1, 2, 3]
    W2 --> Collect
    W3 --> Collect

    Collect --> AST[Tree-Sitter AST Analysis: Symbol Touch Sets]
    AST --> BuildGraph["NetworkX: Build Conflict Graph G = (V, E)"]
    BuildGraph --> SolveMWIS[Solve Maximum Weight Independent Set]
    
    SolveMWIS -->|Certified Independent Set I*| Sandbox[Docker Sandbox: Apply Patches]
    SolveMWIS -->|Conflicted / Unselected Patches| Staging[Staging Queue: Prepare for Rebase]

    Sandbox --> RunTests[Execute Pytest Test Suite]
    RunTests -->|Tests Pass| Commit[Commit I* to Base State s_1]
    RunTests -->|Tests Fail| Rollback[Safety Rollback to Base State s_0]

    Commit --> RebaseEngine[Rebase Staged Patches onto s_1]
    RebaseEngine --> HasRemaining{Remaining Tasks?}
    HasRemaining -->|Yes| NextRound[Schedule Next Optimization Round]
    NextRound --> FanOut
    HasRemaining -->|No| Done([Final Pull Request / Merged Solution])
```

### 6.2 Multi-Agent Coordination Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Benchmark Harness
    participant Sup as LangGraph Supervisor
    participant W1 as Worker Agent 1
    participant W2 as Worker Agent 2
    participant W3 as Worker Agent 3
    participant AST as Tree-Sitter AST Analyzer
    participant Opt as NetworkX MWIS Optimizer
    participant Box as Docker Sandbox Runner
    participant Git as Local Git Workspace

    User->>Sup: Submit Task Backlog (T1, T2, T3)
    Sup->>Git: Create Working Branch (baseline s_0)
    par Task T1
        Sup->>W1: Run Task T1
        W1-->>Sup: Return Proposal Diff p1
    and Task T2
        Sup->>W2: Run Task T2
        W2-->>Sup: Return Proposal Diff p2
    and Task T3
        Sup->>W3: Run Task T3
        W3-->>Sup: Return Proposal Diff p3
    end
    
    Sup->>AST: Ingest Diffs and Compute Symbol Touch Sets
    AST-->>Opt: Emit Detected Symbol Overlaps
    Opt->>Opt: Construct Conflict Graph G = (V, E)
    Opt->>Opt: Solve MWIS (Selected Set I* = p1, p3)
    Sup->>Box: Deploy Selected Set I* to Isolated Container
    Box->>Box: Apply Patches and Run Pytest
    Box-->>Sup: Verification Passed (Score Gain: +18)
    Sup->>Git: Commit Selected Set I* to Baseline (State s_1)
    Sup->>Sup: Rebase Conflicted Patch p2 onto State s_1
    Sup-->>User: Optimization Cycle 1 Complete (Iterate or Done)
```

### 6.3 Realistic Scenario Walkthrough
1. **Input:** A Python repository with 3 bug tickets:
   * *Ticket 1:* Fix division by zero in `math_utils.py:calculate_ratio`.
   * *Ticket 2:* Add input validation type checking to `math_utils.py:calculate_ratio`.
   * *Ticket 3:* Fix incorrect date formatting in `formatters.py:format_iso`.
2. **Worker Execution:**
   * Agent 1 produces patch $p_1$ editing lines 20-30 of `math_utils.py`.
   * Agent 2 produces patch $p_2$ editing lines 15-25 of `math_utils.py`.
   * Agent 3 produces patch $p_3$ editing lines 50-65 of `formatters.py`.
3. **AST Conflict Detection:**
   * The AST analyzer detects that $p_1$ and $p_2$ both modify symbol `math_utils.calculate_ratio`. An edge $(p_1, p_2)$ is added to $E$.
   * Patch $p_3$ touches symbol `formatters.format_iso`, sharing no symbols with $p_1$ or $p_2$.
4. **Graph Formulation:**
   * Nodes: $V = \{p_1, p_2, p_3\}$ with weights $w_1 = 10, w_2 = 8, w_3 = 12$.
   * Edges: $E = \{(p_1, p_2)\}$.
5. **Optimization:**
   * Independent sets: $\{p_1, p_3\}$ (weight $10+12=22$) vs. $\{p_2, p_3\}$ (weight $8+12=20$).
   * Selected: $\mathcal{I}^* = \{p_1, p_3\}$.
6. **Execution & Rebase:**
   * $\{p_1, p_3\}$ are applied to Docker, unit tests pass.
   * State is committed. Patch $p_2$ is rebased against the new `math_utils.py` and scheduled for Round 2.

---

## Chapter 7 — Technology Stack and Justification

| Layer / Component | Chosen Technology | Alternatives Considered | Selection Rationale & Tradeoffs |
| :--- | :--- | :--- | :--- |
| **Language** | **Python 3.12** | Rust, Go, TypeScript | Native ecosystem for AI agents, deep integration with LangGraph, Tree-Sitter bindings, and NetworkX. |
| **Orchestration** | **LangGraph** (v0.2+) | AutoGen, CrewAI, Prefect | Provides explicit state graphs, cyclical graph loops, native parallel `Send` API, and state checkpointing. |
| **AST Parsing** | **Tree-Sitter** (`tree-sitter-python`) | Python `ast`, LibCST | Extremely fast C-based parsing, robust to partial syntax errors, standardized across multiple languages for future expansion. |
| **Graph Modeling** | **NetworkX** (v3.3+) | igraph, Graph-tool | Pure Python, highly maintainable, extensive exact and heuristic clique/independent set algorithms, zero compilation friction. |
| **Linear Programming** | **PuLP** / **SciPy** | Gurobi, CPLEX | Completely free, open-source, permissive license; sufficient for solving fractional chromatic relaxations for $|V| \le 100$. |
| **Sandboxing** | **Docker Engine API** | WebAssembly, gVisor, Podman | Industry-standard container virtualization, precise volume isolation, reproducible dependency containment for target repos. |
| **Test Runner** | **Pytest** | Unittest, Nose | Rich plugin ecosystem, JSON report export capabilities, standard across $\ge 85\%$ of open-source Python projects. |
| **Data Validation** | **Pydantic v2** | Marshmallow, Dataclasses | Ultra-fast Rust-backed schema validation, native serialization with LangGraph states. |

---

## Chapter 8 — Algorithms and Technical Foundations

### 8.1 Algorithm 1: AST Dependency & Conflict Graph Builder

```
Algorithm 1: AST-Based Conflict Graph Construction
--------------------------------------------------------------------------------
Input  : Base Source Tree T_0, Set of Proposed Patches P = {p_1, p_2, ..., p_K}
Output : Undirected Conflict Graph G = (V, E), Symbol Touch Map M

1: Initialize V <- P, E <- {}, M <- {}
2: for each patch p_i in P do:
3:     files_touched <- ExtractFiles(p_i)
4:     symbols_touched <- {}
5:     for each file f in files_touched do:
6:         ast_base <- TreeSitterParse(T_0[f])
7:         diff_ranges <- ExtractLineRanges(p_i, f)
8:         for each range r in diff_ranges do:
9:             enclosing_symbols <- QueryASTNodes(ast_base, r)
10:            symbols_touched <- symbols_touched UNION enclosing_symbols
11:        end for
12:    end for
13:    M[p_i] <- symbols_touched
14: end for
15: // Construct Conflict Edges
16: for i = 1 to K do:
17:    for j = i + 1 to K do:
18:        if FilesOverlap(p_i, p_j) and (M[p_i] INTERSECT M[p_j] != EMPTY) then:
19:            E <- E UNION {(p_i, p_j)}
20:        else if CrossModuleDependency(M[p_i], M[p_j]) then:
21:            E <- E UNION {(p_i, p_j)}
22:        end if
23:    end for
24: end for
25: return G = (V, E), M
--------------------------------------------------------------------------------
```

### 8.2 Algorithm 2: Maximum Weight Independent Set via Fractional Relaxation

The Maximum Weight Independent Set problem is NP-hard. For small agent groups ($|V| \le 20$), exact branch-and-bound via the complement graph's maximum clique is computed:
$$\mathcal{I}^* = \text{MaxClique}(\overline{G})$$

For larger graphs ($|V| > 20$), we solve the Linear Programming relaxation:
$$\max \sum_{i=1}^{|V|} w_i x_i \quad \text{subject to} \quad x_i + x_j \le 1 \quad \forall (i,j) \in E, \quad 0 \le x_i \le 1$$
We round using randomized thresholding certified against the fractional chromatic number $\chi_f(G)$.

```
Algorithm 2: Independent Set Arbiter (MWIS)
--------------------------------------------------------------------------------
Input  : Conflict Graph G = (V, E), Weight Vector W = {w_1, ..., w_K}
Output : Certified Independent Set I*

1: if |V| <= 20 then:
2:     G_comp <- ComplementGraph(G)
3:     cliques <- BronKerboschWithPivoting(G_comp)
4:     I* <- argmax_{C in cliques} sum_{v in C} W[v]
5:     return I*
6: else:
7:     // Linear Programming Relaxation
8:     LP <- InitializeLP(Maximize: sum(W[i] * x[i]))
9:     for each edge (u, v) in E do:
10:        LP.AddConstraint(x[u] + x[v] <= 1.0)
11:    end for
12:    for each node u in V do:
13:        LP.AddConstraint(0.0 <= x[u] <= 1.0)
14:    end for
15:    x_opt <- LP.Solve()
16:    I* <- RandomizedGreedyRounding(x_opt, G)
17:    return I*
18: end if
--------------------------------------------------------------------------------
```

### 8.3 Theoretical Complexity Analysis
* **AST Parsing:** Parsing $F$ files with Tree-Sitter takes $O(F \cdot L)$ where $L$ is file length in tokens. Tree-Sitter operates in linear time.
* **Graph Construction:** Pairwise intersection of $K$ proposals takes $O(K^2 \cdot |\text{Symbols}|)$. For $K \le 20$, this completes in $< 100$ milliseconds.
* **Exact MWIS:** The Bron-Kerbosch algorithm on the complement graph has worst-case time complexity $O(3^{|V|/3})$. For $|V| = 20$, $3^{20/3} \approx 1,476$ operations, which executes in $< 10$ milliseconds on modern CPUs.

---

## Chapter 9 — Data, Interfaces, and Schemas

### 9.1 Data Schemas (`graphmerge.types.schemas`)

#### 9.1.1 Agent Proposal Schema (`AgentProposal`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentProposal",
  "type": "object",
  "properties": {
    "proposal_id": { "type": "string" },
    "agent_id": { "type": "string" },
    "task_id": { "type": "string" },
    "diff_content": { "type": "string" },
    "target_files": { 
      "type": "array", 
      "items": { "type": "string" } 
    },
    "modified_symbols": { 
      "type": "array", 
      "items": { "type": "string" } 
    },
    "local_verified_gain": { "type": "number", "minimum": 0.0 },
    "execution_time_seconds": { "type": "number" },
    "token_usage": {
      "type": "object",
      "properties": {
        "prompt_tokens": { "type": "integer" },
        "completion_tokens": { "type": "integer" }
      },
      "required": ["prompt_tokens", "completion_tokens"]
    }
  },
  "required": ["proposal_id", "agent_id", "task_id", "diff_content", "target_files", "local_verified_gain"]
}
```

#### 9.1.2 Conflict Graph Schema (`ConflictGraphState`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ConflictGraphState",
  "type": "object",
  "properties": {
    "cycle_index": { "type": "integer" },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "weight": { "type": "number" }
        },
        "required": ["id", "weight"]
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": { "type": "string" },
          "target": { "type": "string" },
          "conflict_type": { "type": "string", "enum": ["AST_OVERLAP", "LINE_COLLISION", "IMPORT_DEPENDENCY"] },
          "conflicting_symbol": { "type": "string" }
        },
        "required": ["source", "target", "conflict_type"]
      }
    },
    "selected_independent_set": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["cycle_index", "nodes", "edges", "selected_independent_set"]
}
```

---

## Chapter 10 — Implementation Roadmap

```mermaid
flowchart LR
    subgraph M1 ["Milestone 1: Core Scaffolding (Week 1)"]
        T1["T-01: Environment & Base Image"] --> T5["T-05: LangGraph Fan-Out StateGraph"]
    end

    subgraph M2 ["Milestone 2: AST & Conflicts (Week 2)"]
        T2["T-02: Tree-Sitter Symbol Extractor"] --> T3["T-03: NetworkX Conflict Graph"]
    end

    subgraph M3 ["Milestone 3: Optimization & Sandbox (Week 3)"]
        T4["T-04: MWIS Exact & LP Solver"] --> T6["T-06: Docker Sandbox Runner"]
        T6 --> T7["T-07: Rebase Convergence Loop"]
    end

    subgraph M4 ["Milestone 4: Benchmarks & Reporting (Week 4)"]
        T8["T-08: Baseline Harness Suite"] --> T9["T-09: Empirical Evaluation & Report"]
    end

    M1 --> M2 --> M3 --> M4
```

### Granular Task Specifications

| Task ID | Task Name | Prerequisites | Detailed Execution Steps | Expected Artifacts | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T-01** | Repository & Environment Setup | None | Initialize repo, configure Poetry/Pipenv, install LangGraph, NetworkX, Tree-Sitter, configure linting/pre-commit. | `pyproject.toml`, Dockerfile | Clean `pytest` run with 100% environment health. |
| **T-02** | Tree-Sitter AST Extractor | T-01 | Build `ast_parser.py` using `tree-sitter-python`. Map diff line ranges to AST parent nodes (classes, defs). | `src/graphmerge/analysis/ast_parser.py` | Correctly identifies overlapping function names across 10 synthetic diff fixtures. |
| **T-03** | Conflict Graph Builder | T-02 | Construct NetworkX graph from extracted symbols; link overlapping diffs with typed conflict edges. | `src/graphmerge/optimization/graph_builder.py` | Adjacency matrix perfectly matches theoretical ground truth on 5 test graphs. |
| **T-04** | MWIS Discrete Optimizer | T-03 | Implement Bron-Kerbosch exact solver and PuLP linear programming relaxation. | `src/graphmerge/optimization/solver.py` | Returns valid independent set (0 adjacent edges) on all test graphs. |
| **T-05** | LangGraph State Machine | T-01 | Define `GraphMergeState`, Supervisor node, parallel Worker nodes, and conditional convergence edges. | `src/graphmerge/orchestration/state_graph.py` | State executes cycle 1 and transitions to end state deterministically. |
| **T-06** | Docker Sandbox Execution Engine | T-01 | Implement Docker container controller via `docker-py`. Mount workspace, execute `git apply` and `pytest`. | `src/graphmerge/sandbox/docker_runner.py` | Safely executes tests in isolated container with sub-second execution overhead. |
| **T-07** | Rebase Engine | T-04, T-06 | Implement standard Git 3-way rebase for unselected proposals onto newly committed base commit. | `src/graphmerge/orchestration/rebase.py` | Successfully rebases non-conflicting remaining diffs for Round 2. |
| **T-08** | Baseline Harness Suite | T-05 | Implement Sequential ReAct runner and Naive Git Merge runner for fair empirical comparison. | `benchmarks/baselines/` | Runs all 3 paradigms across the exact same task configurations. |
| **T-09** | Benchmark Experiment Run | T-07, T-08 | Execute 30 paired evaluation trials on synthetic multi-bug repo; log tokens, time, pass rates. | `benchmarks/results/data.json` | Complete empirical data matrix collected with zero runtime crashes. |

---

## Chapter 11 — Testing and Verification Strategy

### 11.1 Multi-Layer Verification Matrix

```
+------------------------------------------------------------------+
|                    Testing & Verification Strategy               |
+------------------------------------------------------------------+
| 1. Unit Tests       | AST symbol extraction, MWIS solver logic,  |
|                     | graph builder edge invariants.             |
| 2. Integration Tests| LangGraph state transitions, Docker volume |
|                     | mounting, patch rebase engine.             |
| 3. System Tests     | End-to-end multi-agent resolution of       |
|                     | 3 synthetic bugs in a sample repository.   |
| 4. Invariant Tests  | Zero conflicting edges in any accepted     |
|                     | Independent Set (Formal Safety Check).     |
+------------------------------------------------------------------+
```

### 11.2 Invariant Verification Tests
The project incorporates **Property-Based Invariant Tests** (using `hypothesis`):
1. **The Independence Invariant:** For any graph $G=(V, E)$ and computed solution $\mathcal{I}^*$:
   $$\forall u, v \in \mathcal{I}^*, \quad (u, v) \notin E$$
   *If this assertion fails, the system halts immediately.*
2. **The Non-Degradation Invariant:** The score of the merged commit $s_1$ in the Docker sandbox must strictly satisfy:
   $$f(s_1) \ge f(s_0)$$
   *If score regresses, the transaction is rolled back.*

---

## Chapter 12 — Evaluation and Benchmarking Plan

### 12.1 Evaluation Metrics

| Metric Name | Formal Definition | Target Threshold | Baseline Comparison |
| :--- | :--- | :--- | :--- |
| **Merge Success Rate (MSR)** | $\frac{\text{Successful Builds with Passed Tests}}{\text{Total Merge Attempts}}$ | $\ge 95\%$ | Naive Git: $\le 60\%$ / LLM-Judge: $\le 75\%$ |
| **Speedup Factor ($S_p$)** | $\frac{T_{\text{sequential}}}{T_{\text{parallel}}}$ | $\ge 2.5\times$ (for $K=5$) | Sequential Execution ($S_p = 1.0\times$) |
| **Preserved Objective Ratio (POR)** | $\frac{\Delta f(\mathcal{I}^*)}{\sum_{i \in \mathcal{I}^*} \Delta f_i}$ | $\ge 1.0$ (Strict additivity) | Naive Merge: $< 0.5$ (Degradation) |
| **Token Cost Overhead ($C_{\text{token}}$)** | $\frac{\text{Total Tokens Used in Parallel + Optimizer}}{\text{Total Tokens in Sequential}}$ | $\le 1.15\times$ | LLM-Judge: $\ge 1.50\times$ |

### 12.2 Benchmarking Experiment Design
* **Dataset:** 30 controlled multi-issue scenarios constructed on a modular Python repository (10 non-conflicting pairs, 10 partially overlapping AST pairs, 10 heavily coupled pairs).
* **Baselines:**
  1. *Baseline 1:* Single-agent Sequential ReAct (Agent 1 $\to$ commit $\to$ Agent 2 $\to$ commit).
  2. *Baseline 2:* Naive Parallel with standard `git merge`.
  3. *Baseline 3:* Naive Parallel with GPT-4o prompted as "Merge Arbitrator".
  4. *Proposed System:* GraphMerge.

---

## Chapter 13 — Risk Analysis

| Risk ID | Risk Description | Severity | Likelihood | Mitigation Strategy | Contingency Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | AST Parser misses dynamic runtime dependency (e.g., `getattr()`). | Medium | Medium | Include conservative file-level edge fallback when dynamic reflection is detected. | Docker sandbox catches test failures and triggers rollback. |
| **RSK-02** | Exact MWIS solver experiences combinatorial explosion on dense graphs. | High | Low | Implement hard threshold ($|V| \le 20$ for exact; switch to LP relaxation above 20). | Set a 1.0-second timeout on the exact solver before falling back to greedy heuristics. |
| **RSK-03** | Docker socket exhaustion or hanging containers during benchmark runs. | Medium | Medium | Strict timeouts (60s) per container execution; automatic container pruning post-run. | Fall back to isolated Python `venv` environments if Docker daemon fails. |
| **RSK-04** | API token rate limits during parallel worker fan-out. | Medium | High | Implement asynchronous token-bucket rate limiting in LangGraph HTTP client. | Use local Ollama instance (e.g., `qwen2.5-coder-7b`) for offline testing. |

---

## Chapter 14 — Resource and Cost Estimation

### 14.1 Hardware and Compute Requirements
* **Development Machine:** Apple Silicon Mac (M1/M2/M3) or x86_64 Linux Workstation with $\ge 16$ GB RAM and 4+ CPU cores.
* **Storage:** 20 GB free disk space for Docker base images and local repository checkouts.

### 14.2 Financial and API Cost Budget
* **Software Tools:** Python, LangGraph, Tree-Sitter, NetworkX, Docker CE are **100% Free & Open Source ($0)**.
* **LLM API Invocations:**
  * For development: Local **Ollama** running `qwen2.5-coder-7b` (**$0.00**).
  * For final benchmark runs (30 trials $\times$ 3 agents $\times$ 3 baselines): Budgeted at **$25.00 – $40.00** via OpenAI/Anthropic APIs.

---

## Chapter 15 — Expected Results and Limitations

### 15.1 Expected Capabilities
* GraphMerge will demonstrate provable non-interference among parallel agents on modular codebases.
* The system will eliminate stochastic hallucination in merge resolution by replacing LLM-based diff synthesis with discrete graph mathematics.
* The system will exhibit near-linear speedup on orthogonal codebase tasks.

### 15.2 Known Practical Limitations
* **Dynamic Language Blindspots:** Pure static AST analysis cannot resolve dynamically generated attribute accesses or runtime dependency injections without running dynamic type inference.
* **Subproblem Independence Assumption:** The system assumes tasks assigned to parallel agents are intended to be concurrent improvements, not mutually contradictory requirements (e.g., Agent 1 asked to delete a feature while Agent 2 is asked to expand it).

---

## Chapter 16 — Project Deliverables and Repository Layout

### 16.1 Target Repository Structure

```
graphmerge/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI verification
├── benchmarks/
│   ├── baselines/               # Sequential and Naive Git baseline runners
│   ├── datasets/                # Synthetic multi-bug test repositories
│   ├── run_benchmark.py         # Main benchmarking execution script
│   └── results/                 # Raw JSON evaluation output
├── docker/
│   ├── Dockerfile.sandbox       # Ephemeral test runner image
│   └── entrypoint.sh
├── docs/
│   ├── architecture.md          # Detailed subsystem specifications
│   └── formal_proofs.md         # Reference proofs from arXiv:2610.30074
├── src/
│   └── graphmerge/
│       ├── __init__.py
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── ast_parser.py    # Tree-Sitter symbol extraction
│       ├── agents/
│       │   ├── __init__.py
│       │   └── worker.py        # LangGraph worker node implementation
│       ├── optimization/
│       │   ├── __init__.py
│       │   ├── graph_builder.py # NetworkX conflict graph construction
│       │   └── solver.py        # MWIS & Fractional LP solver
│       ├── orchestration/
│       │   ├── __init__.py
│       │   ├── state.py         # LangGraph TypedDict schemas
│       │   └── supervisor.py    # Main coordination graph
│       └── sandbox/
│           ├── __init__.py
│           └── docker_runner.py # Docker container test isolation
├── tests/
│   ├── unit/                    # Fast isolated component tests
│   └── integration/             # End-to-end sandbox execution tests
├── pyproject.toml               # Poetry dependencies & build config
└── README.md                    # Project overview & reproduction guide
```

---

## Chapter 17 — Conclusion and Go/No-Go Decision

### 17.1 Go/No-Go Decision Checklist

| Evaluation Criterion | Assessment Status | Evidence / Justification |
| :--- | :--- | :--- |
| **Problem Clarity** | **GO** | Clear, severe bottleneck identified in multi-agent LLM systems (Merge Degradation). |
| **Theoretical Soundness** | **GO** | Rigorously grounded in *arXiv:2610.30074* with formal $1/\chi_f(G)$ guarantees. |
| **Technical Feasibility** | **GO** | Core dependencies (LangGraph, NetworkX, Tree-Sitter) are stable, mature, and open source. |
| **Resource Availability** | **GO** | Runs entirely on a standard developer laptop using local Docker and optional Ollama models. |
| **Novelty & Academic Value** | **GO** | First open-source reference implementation of this optimization model in agent frameworks. |
| **Measurable Success Criteria**| **GO** | Explicit quantitative metrics (MSR $\ge 95\%$, $S_p \ge 2.5\times$, POR $\ge 1.0$). |

**FINAL RECOMMENDATION: GO.** The project is architecturally complete, theoretically sound, and fully specified for development.

---

## References

1. **[arXiv:2610.30074]** Anonymous, *"Parallel AI Agent Collaboration as Graph-Structured Distributed Block Optimization,"* arXiv preprint arXiv:2610.30074 [cs.AI], Oct 2026. [Online]. Available: `https://arxiv.org/abs/2610.30074`
2. **[Yang et al., 2024]** J. Yang, C. E. Jimenez, A. Wettig, et al., *"SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering,"* arXiv preprint arXiv:2405.15793 [cs.SE], 2024.
3. **[Wu et al., 2023]** Q. Wu, G. Bansal, J. Zhang, et al., *"AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,"* arXiv preprint arXiv:2308.08155 [cs.AI], 2023.
4. **[LangChain, 2024]** LangChain Inc., *"LangGraph: Building Language Agents as Graphs,"* Official Documentation, 2024. [Online]. Available: `https://langchain-ai.github.io/langgraph/`
5. **[Leßenich et al., 2018]** S. Leßenich, S. Apel, and C. Kästner, *"Semantic Merge Conflict Detection in Component-Based Software Systems,"* *IEEE Transactions on Software Engineering*, vol. 44, no. 5, pp. 439–462, 2018.
6. **[Bron & Kerbosch, 1973]** C. Bron and J. Kerbosch, *"Algorithm 457: finding all cliques of an undirected graph,"* *Communications of the ACM*, vol. 16, no. 9, pp. 575–577, 1973.

---

## Checklist: Before Writing the First Line of Code

### Top 5 Priority Actions to Take Immediately:
1. **Initialize Git & Poetry Environment:** Create the GitHub repository, set Python to `3.12`, and lock dependencies (`langgraph`, `networkx`, `tree-sitter`, `tree-sitter-python`, `pydantic`).
2. **Build the Minimal AST Spikeworks:** Write a 40-line standalone test script in `tests/spike_ast.py` that parses two simple Python functions using `tree-sitter` and asserts their symbol bounding boxes.
3. **Set Up the Docker Sandbox Baseline:** Create the base test container Dockerfile and verify that `docker-py` can mount a local directory, apply a test patch, and capture `pytest` exit codes in $< 1.5$ seconds.
4. **Implement the NetworkX MWIS Unit Test:** Write the exact Bron-Kerbosch complement clique finder on a small 5-node synthetic graph to verify mathematical correctness before wiring it into LangGraph.
5. **Present the Chapter 5 Architecture Diagram to Your Professor:** Share the architecture diagram and the problem-to-solution matrix with your academic advisor to finalize approval before full implementation.
