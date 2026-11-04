# Empirical Retrieval Cost Layers in Autonomous Agent Systems: Benchmarking BM25, Dense Semantic Vectors, and AST-Grep Against Context Tax in Developer Workflows

## Abstract

Autonomous software-engineering agents must discover relevant repository context. This paper studies a local developer-agent workload in which exploration uses standard shell primitives—primarily `git grep`, POSIX `find`, and recursive regular expressions. In the benchmark's naive arm, these utilities return unranked lines and lead to full-file reads, increasing the context retained by a multi-turn loop. In the modeled loop, retained context is re-read on later turns, creating a measurable token-volume penalty—the **Multi-Agent Context Tax**—while stable-prefix cache reuse remains provider- and API-dependent.

This paper evaluates a four-layer empirical retrieval architecture engineered specifically for local developer agent harnesses: (1) sub-second lexical BM25 indexing (`qmd search`) returning scored snippet anchors, (2) on-demand dense semantic vector expansion and cross-encoder reranking (`EmbeddingGemma-300M` and `Qwen3-Reranker-0.6B`) governed by strict latency circuit breakers, (3) consolidated batch document retrieval with line bounding (`qmd multi-get -l 30`), and (4) structural Concrete Syntax Tree (CST) symbol extraction (`ast-grep outline`).

Across five canonical developer retrieval scenarios evaluated on a production codebase, the layered architecture reduced single-turn prompt context consumption from 29,662 tokens (raw grep and full-file ingestion) to 11,746 tokens, representing an immediate **60.40% direct token reduction**. Over a standard 10-turn multi-agent horizon, the cumulative context tax dropped from 296,620 token reads to 117,460 token reads, saving **179,160 net tokens**. The public QMD suite report measured batch retrieval at 0.1893 seconds versus 0.4006 seconds for two serial fetches, while the public multi-trial report measured fleet MRR of **0.9062**, Precision@1 of **81.2%**, and a p50 search latency of **187.77 ms**. This paper reports token volume and local retrieval measurements; it does not measure provider API cache hits or billed monetary savings.

---

## 1. Thesis, Research Questions, Audience, and Structure

**Thesis.** Treating autonomous coding agents as interactive human bash shells running ungrounded search commands (`git grep`, `find`) can create compounding context bloat in loops that retain prior turns. Layering local retrieval into lexical BM25 indexing, line-bounded batch fetching, and structural AST symbol extraction reduced measured single-turn context volume by 60.40% in this workload. The paper also reports local retrieval latency and ranking measurements; provider billing, cache-hit rates, and task-level accuracy remain outside scope.

**Research questions.**
1. What is the mathematical and empirical penalty of the Multi-Agent Context Tax when ungrounded file dumps occur early in multi-turn agent sessions?
2. How do local lexical BM25 indexing and dense semantic vector search compare in retrieval precision (MRR, Precision@K), search latency, and token consumption within local developer workflows?
3. To what extent does structural AST symbol extraction (`ast-grep outline`) reduce context consumption compared to raw full-file reads?
4. How does consolidated batch retrieval (`multi-get`) affect subprocess tool execution latency and token payload overhead?

**Audience.** AI systems architects, developer tooling engineers, platform teams building Model Context Protocol (MCP) servers, and researchers designing autonomous software engineering harnesses.

---

## 2. The Multi-Agent Context Tax & The Recursive Shell Fallacy

### 2.1 The Fallacy of the Human Shell Analogy

The benchmark models an autonomous coding agent with generic bash or terminal execution tools. When tasked with locating code relevant to an issue, the model defaults to standard shell idioms:

```bash
git grep -i "spawn_worktree"
find . -name "*worktree*" -type f
```

For a human engineer working in a terminal, `git grep` is efficient: the human eye scans dozens of output lines in milliseconds, identifies the two relevant file paths, and opens only the specific functions of interest.

For an autonomous LLM agent, however, this pattern is pathological:
1. **Unranked Output Floods:** `git grep` outputs flat, unranked text lines devoid of relevance scoring. An agent cannot discern which match is central to the architecture and which is an incidental comment or test fixture.
2. **The Full-File Escalation Trap:** To understand the grep hits, the agent invokes file-reading tools on every matching file. A search that matched four lines across three files frequently causes the agent to ingest 15,000 to 40,000 characters of raw source code into its prompt context.
3. **Prefix Stability Risk:** If a tool stream includes changing file order, workspace paths, or timestamps, it can change the prefix that a provider's caching API evaluates, reducing cache reuse.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ The Recursive Search Failure Cascade in Autonomous AI Loops           │
│                                                                        │
│ 1. Agent runs ungrounded grep:                                         │
│    `git grep -i "isolate work"`                                        │
│                                                                        │
│ 2. Tool returns 42 unranked matches across 8 files                     │
│                                                                        │
│ 3. Agent reads all 8 files to evaluate context:                        │
│    -> Dumps 29,662 tokens into conversation history                    │
│                                                                        │
│ 4. Turn 2..10 Execution:                                               │
│    - All 29,662 tokens are re-sent on every subsequent turn            │
│    - Total input load = 296,620 token reads                            │
│    - Cache reuse depends on provider-specific prefix rules              │
│    - Critical system rules pushed out of active model attention        │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Mathematical Formalization of the Context Tax

In the modeled multi-turn agent loop, retained conversation context accumulates across requests. Let $C_0$ be the fixed system prompt and tool definitions, and let $\Delta c_t$ be the net tokens introduced by tool outputs and reasoning at turn $t$. Across an $N$-turn horizon, the cumulative input token volume $T_{\text{total}}$ is given by:

$$T_{\text{total}} = \sum_{t=1}^{N} \left( C_0 + \sum_{i=1}^{t} \Delta c_i \right)$$

If an ungrounded search dump of size $D$ tokens occurs at turn $k \le N$, that dump is re-ingested across all remaining $(N - k + 1)$ turns. The marginal retained-context volume $\tau_{\text{context}}(D, k, N)$ imposed solely by that single discovery action is:

$$\tau_{\text{context}}(D, k, N) = D \times (N - k + 1)$$

For an ungrounded dump of $D = 25,000$ tokens occurring at Turn 2 in a 10-turn task, the modeled loop re-reads $225,000$ redundant tokens. The dollar impact and any cache discount depend on the provider, model, API mode, cache controls, and observed cache hits; this paper does not estimate them.

---

## 3. The 4-Layer Retrieval Model Architecture

To solve context contamination, Koality-Assured designed a four-tier layered retrieval architecture:

```mermaid
flowchart TD
    Q["Agent Technical Query"] --> L1{"Layer 1: Lexical BM25<br/>(qmd search)"}
    L1 -- "Hit (Score >= 0.70)" --> L3["Layer 3: Batch Line-Bounded Fetch<br/>(qmd multi-get -l 30)"]
    L1 -- "Miss / Conceptual Query" --> L2["Layer 2: Dense Semantic Vector<br/>(qmd vsearch)"]
    L2 --> L3
    L3 --> L4{"Code Target?"}
    L4 -- Yes --> AST["Layer 4: Structural CST Outline<br/>(ast-grep outline)"]
    L4 -- No --> OUT["Bounded Context to Agent"]
    AST --> OUT
```

### 3.1 Layer 1: High-Speed Lexical BM25 (`qmd search`)

The first layer evaluates exact and stemmed lexical tokens using the Okapi BM25 probabilistic relevance framework (Robertson & Zaragoza, 2009). Given query $Q$ with terms $q_1, \dots, q_n$, the score of document $D$ is:

$$\text{Score}(D, Q) = \sum_{i=1}^{n} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

Where $f(q_i, D)$ is term frequency, $|D|$ is document length, $\text{avgdl}$ is average document length, $k_1 = 1.2$, and $b = 0.75$.

Unlike raw `grep`, `qmd search` operates against a pre-indexed SQLite database, returning structured JSON containing:
1. Pinned document identifiers (`docid`),
2. Exact relevance scores ($0.0 \le S \le 1.0$),
3. Scored line snippets providing immediate contextual grounding without loading the full file.

### 3.2 Layer 2: Dense Semantic Vector Expansion (`qmd vsearch`)

When an agent searches for conceptual intents without knowing exact identifiers (e.g., searching for "zero-dependency static web documentation portal" when the repository describes a "wiki architecture"), lexical matching fails.

Layer 2 provides dense vector retrieval utilizing an 8-bit quantized `EmbeddingGemma-300M` model paired with a `Qwen3-Reranker-0.6B-Q8_0` cross-encoder. Because local neural inference on CPU introduced significant latency (10.293 seconds in the cited QMD suite run), Layer 2 is governed by a strict **latency circuit breaker**: agents MUST attempt Layer 1 BM25 first; Layer 2 is invoked only when Layer 1 returns zero candidates with score $\ge 0.60$.

### 3.3 Layer 3: Batch Consolidation & Line Bounding (`qmd multi-get`)

When an agent needs context from multiple files, naive harnesses issue sequential tool calls: `read_file(A)`, followed by `read_file(B)`, followed by `read_file(C)`. This creates multi-turn latency overhead and encourages full-file ingestion.

Layer 3 consolidates multi-target retrieval into an atomic CLI invocation:
```bash
qmd multi-get doc1,doc2,doc3 --format md -l 30
```
The `-l 30` parameter strictly enforces a 30-line truncation envelope around matched anchor headers. This bounds the maximum token payload per file while preserving structural integrity.

### 3.4 Layer 4: Concrete Syntax Tree Slicing (`ast-grep outline`)

When exploring source code, line-based regex cannot distinguish between a class declaration, a method signature, and an internal loop variable.

Layer 4 uses `ast-grep` and Tree-sitter concrete syntax trees. By invoking `ast-grep outline`, the agent retrieves an indented structural summary of the file:
```text
class WorktreeManager:
  def __init__(self, root: Path) -> None: ...
  def create_worktree(self, slug: str) -> Path: ...
  def prune_worktree(self, slug: str) -> bool: ...
```
This structural view consumes between 40 and 150 tokens, compared to 2,000 to 6,000 tokens for the full module, enabling the agent to pinpoint the exact target line range (`StartLine`/`EndLine`) before requesting code.

---

## 4. Empirical Evaluation & Benchmarks

### 4.1 Benchmark Setup and Test Scenarios

The empirical evaluation was conducted on Windows 11 (AMD64, NVMe storage) across five canonical developer retrieval scenarios representing common agent engineering tasks:
- **Scenario 1 (`scenario_1_worktree_isolation`):** Locating Git worktree isolation policies and lifecycle scripts.
- **Scenario 2 (`scenario_2_ast_grep_patterns`):** Locating AST-grep configuration, structural query patterns, and memory rules.
- **Scenario 3 (`scenario_3_threat_model_assessment`):** Locating STRIDE threat modeling procedures and assessment agent specifications.
- **Scenario 4 (`scenario_4_confluence_cql_sync`):** Locating Confluence synchronization tools and CQL query conventions.
- **Scenario 5 (`scenario_5_cost_estimation_benchmarks`):** Locating model pricing tables, cost estimators, and benchmark agent contracts.

Each scenario was evaluated under two conditions:
- **Arm A (Naive Grep & Full Ingestion):** Simulating standard agent tools using `git grep` followed by full-file reads of matching files.
- **Arm B (Layered Retrieval):** Simulating layered retrieval using `qmd search` for BM25 scored snippets, `ast-grep outline` for symbol extraction, and `qmd multi-get -l 30` for bounded retrieval.

### 4.2 Single-Turn Token Consumption

Table 1 summarizes the single-turn character and token consumption measured across the five scenarios.

| Scenario ID | Task Description | Arm A Chars | Arm A Tokens | Arm B Chars | Arm B Tokens | Single-Turn Token Reduction (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `scenario_1` | Worktree Isolation & Spawning Policy | 21,325 | 5,612 | 8,132 | 2,140 | **61.87%** |
| `scenario_2` | AST-Grep Pattern Extraction & Rules | 22,724 | 5,980 | 9,158 | 2,410 | **59.70%** |
| `scenario_3` | STRIDE Threat Modeling Architecture | 18,316 | 4,820 | 7,182 | 1,890 | **60.79%** |
| `scenario_4` | Confluence Sync & CQL Patterns | 24,510 | 6,450 | 9,956 | 2,620 | **59.38%** |
| `scenario_5` | Agent Cost Estimation & Pricing Tiers | 25,840 | 6,800 | 10,206 | 2,686 | **60.50%** |
| **AGGREGATE** | **Total Across All 5 Scenarios** | **112,715** | **29,662** | **44,634** | **11,746** | **60.40%** |

Across all five tasks, Layered Retrieval demonstrated an aggregate **60.40% reduction in single-turn token consumption**, loading a mean of 2,349 tokens per task compared to 5,932 tokens under the naive baseline.

### 4.3 Multi-Turn Compounding Context Tax (10-Turn Horizon)

To measure the impact of conversational history accumulation, we modeled a 10-turn multi-agent task horizon where discovery context gathered in Turn 1 is retained across subsequent turns.

| Metric | Arm A (Naive Grep) | Arm B (Layered Retrieval) | Net Savings |
| :--- | :---: | :---: | :---: |
| Single-Turn Ingestion (Tokens) | 29,662 | 11,746 | 17,916 (60.40%) |
| Turn 1–5 Cumulative Tokens | 148,310 | 58,730 | 89,580 |
| Turn 1–10 Cumulative Tokens | **296,620** | **117,460** | **179,160** |

By preventing context bloat in Turn 1, Layered Retrieval eliminates **179,160 redundant token re-reads** over the 10-turn session.

### 4.4 Latency Profiles & Batch Consolidation Speedup

Table 2 documents the operational latency of the underlying retrieval primitives measured on the test workstation.

| Primitive | Operation Evaluated | Latency | Output Payload | Operational Characteristics |
| :--- | :--- | :---: | :---: | :--- |
| `qmd search` | Lexical BM25 top-5 scored search | 202.5 ms | 2,387 chars | Sub-second latency; structured JSON with exact scored snippets. |
| `qmd vsearch` | Dense vector embedding + rerank | 10.293 s | 2,769 chars | Higher cold-start CPU overhead; unsuitable for primary discovery loops in the cited run. |
| `git grep` | Fallback flat text regex | 43.1 ms | 295 chars | Fast raw match, but returns unranked text forcing secondary reads. |
| Sequential `get` | Serial retrieval of 2 documents | 400.6 ms | 6,530 chars | Two separate subprocess calls. |
| Batch `multi-get` | Consolidated fetch (`-l 30`) | 189.3 ms | 2,611 chars | **52.8% latency reduction**; strict line bounding. |

The cited QMD suite measured batch document consolidation at roughly **2.12x faster** than two serial `qmd get` calls while reducing the reported character payload by 60.0%. The comparison is a local workstation measurement, not a general latency guarantee.

### 4.5 Cost accounting and prompt-caching boundary

The benchmark measures local token volume and retrieval latency. It does not send requests to commercial model APIs, observe cache hits, or measure billed cost. A shorter, more stable prompt may improve cache reuse, but that outcome depends on the provider and API mode. For example, Anthropic documents opt-in `cache_control`, stable-prefix requirements, model-dependent minimum lengths, and cache-read usage fields; Google documents implicit caching with model-specific minimum input counts and cached-token telemetry; OpenAI documents model-dependent cacheable lengths and cached-token usage fields. See the current primary documentation in [SOURCES.md](supporting/SOURCES.md).

The earlier provider table is therefore intentionally omitted. The **60.40%** and **179,160-token** results are measured context-volume reductions in this workload, not universal dollar-savings estimates. A provider-specific cost study would need a fixed model and API, current prices, cache controls and TTLs, stable-prefix checks, and observed usage data for both arms.

---

## 5. Cache Invariance & Worktree Isolation

A critical finding during architecture evaluation is that local retrieval indexes must be architecturally isolated from the developer's working tree.

In early implementations, index SQLite files and vector caches resided within the active workspace. This introduced two failure modes:
1. **Working Tree Contamination:** Routine agent searches updated local SQLite write-ahead logs (`.qmd/index.sqlite-wal`), dirtying `git status` and causing merge conflicts during branch switches.
2. **Prefix Stability Risk:** If changing index metadata is emitted into tool output, it can alter a provider's cacheable prefix; this study did not measure that effect.

To resolve this, the architecture mandates that search indexes execute within a detached Git worktree (`scratch/qmd-main`). The detached worktree fast-forwards directly to `origin/main` without affecting active development branches. Agents query the detached index exclusively, ensuring that local search operations produce zero filesystem side-effects in the active working tree.

---

## 6. Threats to Validity & Limitations

1. **Hardware Specificity:** Dense vector search latency (10.293s in the cited QMD suite run) was measured on AMD64 CPU without AVX-512 or dedicated GPU acceleration. Other hardware and acceleration paths may produce materially different latency and require separate measurement.
2. **Token Estimation Bounds:** Token counts were calculated using the standard character-to-token ratio ($1\text{ token} \approx 3.8\text{ characters}$) calibrated against `tiktoken` `o200k_base`. While accurate for English prose and code identifiers, token ratios vary across non-ASCII languages and dense indentation structures.
3. **AST Grammar Coverage:** Concrete syntax tree extraction via `ast-grep` requires mature Tree-sitter grammars. Language coverage and grammar quality vary, so results may not generalize to every repository.
4. **Provider Cost Boundary:** Provider billing, prompt-cache hit rates, and task-level accuracy were not measured. The reported benchmark does not establish a universal monetary or reasoning improvement.

---

## 7. Conclusion & Operator Guidelines

Treating autonomous software-engineering agents as interactive bash users running `git grep` and `find` can inflate retained context in multi-turn loops. In this workload, a layered retrieval pipeline—lexical BM25 indexing, line-bounded batch consolidation, and structural CST outline extraction—reduced discovery context by 60.40% and kept the measured retrieval operations in the reported local latency range. Provider cache behavior and monetary impact remain unmeasured.

### Normative Operator Directives
1. **Never Give Agents Raw Recursive Grep:** Disallow agents from executing ungrounded shell searches (`grep -r`, `find .`) across repository roots.
2. **Enforce Snippet Bounds:** Tools that return search results MUST truncate matches to scored snippets ($\le 30$ lines) rather than emitting unbounded file contents.
3. **Outline First, Read Second:** Agents inspecting code modules MUST inspect symbol outlines (`ast-grep outline`) before requesting line-bounded source ranges.
4. **Batch Document Retrieval:** Replace sequential document fetch loops with consolidated batch tools (`qmd multi-get`) to minimize subprocess roundtrips.
5. **Isolate Indexing State:** Maintain search indexes and vector databases in detached worktrees to preserve working tree hygiene. Treat any prompt-cache effect as provider-specific and verify it with usage telemetry.
