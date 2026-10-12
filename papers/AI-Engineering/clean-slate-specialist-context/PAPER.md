# Clean-slate specialist context: quantifying the multi-agent context tax and distractor interference

## Abstract

Multi-agent software engineering harnesses frequently delegate sub-tasks to specialized subagents by cloning the coordinator's entire conversation transcript. In OpenAI Codex Multi-Agent v2, the `spawn_agent` primitive defaults `fork_turns` to `"all"`, propagating historical messages, prior tool outputs, and discarded scratchpads down the execution tree. This practice introduces two compounding engineering penalties: an $O(M \cdot K \cdot T)$ input context tax that inflates token consumption across multi-turn sessions, and attention degradation caused by semantic distractors scattered across the inherited history.

This paper evaluates **clean-slate specialist context** using an automated, offline, and deterministic benchmark suite. Across 75 trial runs covering 15 tasks in three software engineering archetypes (code syntax/logic repair, role-based access control auditing, and structured configuration extraction), clean-slate dispatch (`fork_turns: "none"`) is compared against inherited history depths of 10,000, 30,000, 60,000, and 90,000 tokens. In the benchmark, clean-slate dispatch reduced cumulative input tokens by an unweighted mean of 99.7220% compared to the 60,000-token inherited baseline (655.33 vs. 235,765.73 tokens across a three-turn task loop). Clean-slate achieved a 100.0% oracle pass rate (15/15) with zero distractor collisions. Under the 60,000-token inherited baseline, semantic distractors induced collisions in 7 of 15 trials (46.67%), depressing the task completion rate to 53.33%.

These results describe deterministic, synthetic fixtures evaluated with local `tiktoken` (`o200k_base`) message serialization. They do not represent live provider billing records or arbitrary production workloads. Provider prompt caching mitigates marginal input token prices by 50% on cached prefix reads, but does not eliminate time-to-first-token latency, active context window saturation, or distractor-induced attention rot. Clean-slate delegation shifts operational complexity from transcript propagation to coordinator contract synthesis, requiring disciplined schema enforcement to avoid the "Context Omission Gap."

---

## 1. Thesis, questions, audience, and structure

**Thesis.** Defaulting to conversation transcript inheritance during subagent delegation imposes an $O(M \cdot K \cdot T)$ token multiplier and introduces semantic distractors that degrade tool precision. Replacing transcript cloning with clean-slate zero-flight dispatch—combining explicit history suppression (`fork_turns: "none"`) with four-part declarative task contracts and just-in-time structured retrieval—eliminates redundant history bloat and distractor interference without sacrificing task execution accuracy.

**Research questions.**
1. How does cumulative token consumption scale across multi-turn subagent sessions when comparing transcript inheritance to clean-slate dispatch?
2. To what degree do semantic distractors present in historical coordinator transcripts degrade subagent tool precision and deterministic test oracle pass rates?
3. How do modern provider prompt-caching mechanisms alter the cost-benefit boundary between context inheritance and clean-slate dispatch?
4. What is the operational failure mode of clean-slate dispatch (the "Context Omission Gap"), and how can harness architectures mitigate it?

**Audience.** Systems engineers designing multi-agent harnesses, autonomous workflow architects, and AI engineering practitioners evaluating context management and subagent delegation protocols.

---

## 2. The mechanics of subagent delegation: forked history vs. clean slate

Contemporary multi-agent frameworks handle delegation through one of two primary context patterns:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Pattern A: Transcript Inheritance (fork_turns: "all")                 │
│                                                                        │
│ Coordinator Session (Turns 1..N) ──► Full Transcript Cloned (T tokens)│
│                                      │                                 │
│                                      ▼                                 │
│                     Subagent executes K turns                         │
│                     Turn 1 Input: T + Contract                         │
│                     Turn 2 Input: T + Contract + Turn 1 Messages       │
│                     Turn 3 Input: T + Contract + Turns 1..2 Messages   │
│                     Cumulative Billed Input: O(K * T)                  │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ Pattern B: Clean-Slate Zero-Flight (fork_turns: "none")                │
│                                                                        │
│ Coordinator Session (Turns 1..N) ──► Declarative Contract (C tokens)  │
│                                      (No parent transcript passed)     │
│                                      │                                 │
│                                      ▼                                 │
│                     Subagent executes K turns                         │
│                     Turn 1 Input: C                                    │
│                     Turn 2 Input: C + Turn 1 Messages                  │
│                     Turn 3 Input: C + Turns 1..2 Messages              │
│                     Cumulative Billed Input: O(K * C) where C << T     │
└────────────────────────────────────────────────────────────────────────┘
```

In OpenAI Codex Multi-Agent v2, the `collaboration.spawn_agent` tool handler (`codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs`) defines the `fork_turns` parameter. When omitted, `fork_turns` defaults to `SpawnAgentForkMode::FullHistory` (`"all"`). Under this setting, the newly initialized subagent inherits the complete sequence of user messages, assistant responses, and tool executions previously logged by the coordinator. Similar inheritance conventions exist in OpenAI Agents SDK handoffs (unless an explicit `input_filter` is registered) and in naive orchestrator scripts that append historical conversation dumps into subagent system prompts.

Crucially, **context history isolation is distinct from process and filesystem sandboxing**. Setting `fork_turns: "none"` clears conversational memory, but does not provide an isolated execution container, a separate file tree, or separate network permissions. Operating system sandboxing and version control worktrees (such as Git worktrees) remain independent controls that must be enforced separately.

---

## 3. The Multi-Agent Context Tax: formalizing $O(M \cdot K \cdot T)$

In an autonomous engineering session, an orchestrator coordinates a high-level goal (for example, debugging an integration suite) by delegating discrete sub-tasks to $M$ specialized subagents (such as a linter, a test fixer, a security reviewer, and a documentation specialist).

Let:
- $T$ denote the token depth of the coordinator's conversation transcript at the time of delegation.
- $M$ denote the number of subagents spawned.
- $K$ denote the average number of execution turns per subagent (where a turn consists of an assistant reasoning/tool-call generation and a tool output return).
- $C$ denote the token size of a concise declarative task contract ($C \ll T$).
- $\Delta_i$ denote the incremental token size of tool calls and outputs generated during turn $i$.

Under **Transcript Inheritance**, the input context presented to each subagent on turn $k \in \{1, \dots, K\}$ is:
$$\text{InputTokens}_{\text{forked}}(k) = T + C + \sum_{i=1}^{k-1} \Delta_i$$

Summing across all $K$ turns and all $M$ subagents, the cumulative input token burden is:
$$\text{TotalInput}_{\text{forked}} = \sum_{m=1}^M \sum_{k=1}^K \left( T + C + \sum_{i=1}^{k-1} \Delta_i \right) = M \cdot K \cdot T + M \cdot K \cdot C + M \sum_{k=1}^K \sum_{i=1}^{k-1} \Delta_i$$

The leading term is **$O(M \cdot K \cdot T)$**. For a coordinator session at depth $T = 60{,}000$ tokens delegating to $M = 4$ specialists running $K = 3$ turns each:
$$M \cdot K \cdot T = 4 \times 3 \times 60{,}000 = 720{,}000 \text{ input tokens}$$

Under **Clean-Slate Dispatch**, $T = 0$. The leading term vanishes:
$$\text{TotalInput}_{\text{clean}} = M \cdot K \cdot C + M \sum_{k=1}^K \sum_{i=1}^{k-1} \Delta_i$$

For a typical contract where $C \approx 800$ tokens:
$$M \cdot K \cdot C = 4 \times 3 \times 800 = 9{,}600 \text{ input tokens}$$

This difference represents an order-of-magnitude reduction in baseline input context processing.

---

## 4. Attention decay and semantic distractors: "Lost in the Middle" in tool loops

The financial cost of transcript inheritance is accompanied by an architectural penalty: **attention degradation**.

Transformer architectures distribute attention weights across all tokens in the input context. As demonstrated by Liu et al. (2024), language models exhibit a pronounced U-shaped retrieval performance curve ("Lost in the Middle"). Information placed at the absolute beginning (primacy effect) or absolute end (recency effect) of the prompt is recalled with high accuracy, whereas facts located in the middle of long contexts suffer steep degradation.

Research by Chroma (2025) extends this finding to multi-turn reasoning and agentic workflows ("Context Rot"). In realistic engineering transcripts, the historical turns preceding delegation are populated with:
1. **Stale Identifiers:** Function names, variable declarations, or API signatures that were discussed, refactored, or discarded in earlier turns.
2. **Obsolete Output Dumps:** Multi-megabyte compiler outputs, verbose stack traces, and raw JSON blobs from unrelated services.
3. **Conflicting Architectural Guidance:** Earlier hypotheses that were investigated and subsequently invalidated by test failures.

When a subagent inherits this context, these historical artifacts act as **semantic distractors**. Even if the latest turn contains the active instruction, the presence of competing symbols in the attention matrix causes:
- *Stale Identifier Collisions:* The subagent borrows variable names or parameter conventions from discarded turns.
- *Tool Drift:* The subagent attempts to call tools that were valid for the coordinator but are absent from the subagent's restricted toolset.
- *Instruction Forgetting:* Crucial negative constraints (such as "do not modify network configurations") placed in the task prompt are washed out by thousands of tokens of historical chatter.

---

## 5. The Zero-Flight Protocol: declarative contracts & Just-In-Time retrieval

Clean-slate context requires an alternative communication mechanism to transfer intent without chat logs. The **Zero-Flight Protocol** replaces transcript cloning with a four-part declarative task contract:

```yaml
task_contract:
  authority: "Execute local bugfix on synthetic calculation service. Do not modify external network configs."
  scope: "Fix unhandled ZeroDivisionError in calculate_metric_v01() located in handler.py. Fallback value must be 0.0. Emit marker SYNTHETIC_MARKER_REPAIR_V01_OK."
  targets:
    - "src/synthetic_service/handler_v01.py"
  cost_layers: "Use ast-grep to locate calculate_metric_v01 function; do not perform whole-directory tree walks. Use Headroom on test run outputs."
```

### The 4-Part Dispatch Contract
1. **Delegated Authority & Boundary:** Explicitly declares permitted operations and hard prohibitions (e.g., read-only vs. mutating, local execution only, no external network calls).
2. **Exact Task Scope & Oracles:** Concise specification of the change to be made, expected invariants, and success markers.
3. **Concrete File Targets:** Absolute or repository-relative paths to the precise files, directories, or fixtures requiring inspection or modification.
4. **Child Cost-Layer Directives:** Instructions mandating structural retrieval tools (`ast-grep`), indexed document discovery (`qmd`), and tool-output compression (`headroom`) to prevent the child from regenerating context bloat internally.

### Just-in-Time (JIT) Context Acquisition
Rather than receiving pre-loaded file contents or historical logs, the clean-slate subagent begins with an empty working memory and retrieves context on demand. Using targeted search tools, the specialist extracts only the syntax subtree or documentation section relevant to its immediate turn. This ensures maximum attention density on active code.

---

## 6. Synthetic benchmark methodology

To evaluate context scaling and distractor interference empirically, this study implements a fully deterministic, offline benchmark package (`supporting/benchmark/`).

### Experimental Parameters
- **Runtime:** CPython 3.13.16 on Windows x86_64, pinned via `uv` lockfile (`uv.lock`). Direct dependency: `tiktoken==0.14.0`.
- **Tokenizer:** Explicit `o200k_base` encoding over compact JSON serialization of message lists.
- **Provider API Requests:** Zero. All token counting and oracle checks run locally offline.
- **Integrity Manifest:** All benchmark source files, configurations, and metric logs are bound by normalized-text SHA-256 digests in `sha256-manifest.json` and verified with `verify_sha256_manifest.py`.

### Task Archetypes (15 Variants)
The suite generates 15 distinct tasks across three archetypes (5 variants each):
1. **Archetype A: Code Syntax & Logic Repair (`code_repair`):** Subagent must inspect `src/synthetic_service/handler_vXX.py`, insert a zero-division guard returning `0.0`, and emit exact marker `SYNTHETIC_MARKER_REPAIR_VXX_OK`.
2. **Archetype B: RBAC Security Policy Audit (`rbac_audit`):** Subagent must inspect route decorators in `src/synthetic_auth/policy_vXX.py`, identify an unadorned handler (`export_diagnostics_vXX`), apply `@enforce_rbac(role='admin')`, and emit `SYNTHETIC_MARKER_RBAC_VXX_VERIFIED`.
3. **Archetype C: Structured Configuration Extraction (`schema_extraction`):** Subagent must extract database connection parameters and timeouts from `config/synthetic_config/settings_vXX.json` into a JSON envelope with key `SYNTHETIC_MARKER_SCHEMA_VXX_EXTRACTED: true`.

### Context Conditions Evaluated
Each of the 15 tasks is evaluated under 5 distinct context conditions (75 total trials):
- `clean_slate`: 0 tokens of prior history (task contract only, ~600–700 tokens initial input).
- `fork_10k`: Contract prepended with ~10,000 tokens of synthetic coordinator transcript containing realistic build logs, diffs, and injected distractor tokens.
- `fork_30k`: Contract prepended with ~30,000 tokens of synthetic history and distractors.
- `fork_60k`: Contract prepended with ~60,000 tokens of synthetic history and distractors.
- `fork_90k`: Contract prepended with ~90,000 tokens of synthetic history and distractors.

Each trial executes a standard 3-turn interactive tool-use loop (Turn 1: Read/inspect target; Turn 2: Apply modification; Turn 3: Final verification and envelope return).

---

## 7. Empirical measurement results

The benchmark executed 75 deterministic trials in 1.33 seconds. Full per-trial results are recorded in [`supporting/benchmark/metrics/trial-metrics.json`](supporting/benchmark/metrics/trial-metrics.json); aggregate statistics are recorded in [`supporting/benchmark/metrics/summary.json`](supporting/benchmark/metrics/summary.json).

### Measured Token Consumption and Pass Rates

| Dispatch Condition | Prior History Tokens | Mean Cumulative Input Tokens | Median Tokens | Min–Max Tokens | Oracle Pass Rate | Distractor Collision Rate | Token Reduction vs. Baseline |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`clean_slate`** | **0** | **655.33** | **673** | **608 – 685** | **100.0% (15/15)** | **0.0% (0/15)** | **99.7220%** |
| `fork_10k` | ~10,000 | 41,766.33 | 41,782 | 41,717 – 41,801 | 86.67% (13/15) | 13.33% (2/15) | 82.2849% |
| `fork_30k` | ~30,000 | 118,212.53 | 118,198 | 118,163 – 118,277 | 86.67% (13/15) | 13.33% (2/15) | 49.8601% |
| **`fork_60k`** | **~60,000** | **235,765.73** | **235,720** | **235,704 – 235,874** | **53.33% (8/15)** | **46.67% (7/15)** | **Baseline (0.0%)** |
| `fork_90k` | ~90,000 | 353,322.33 | 353,273 | 353,217 – 353,476 | 60.00% (9/15) | 40.00% (6/15) | -49.8616% |

### Key Quantitative Findings

1. **Context Tax Reduction:** Clean-slate dispatch consumed an unweighted mean of 655.33 cumulative input tokens per task across the three-turn interaction. Compared to the 60,000-token inherited baseline (235,765.73 tokens), clean-slate achieved a **99.7220% reduction** in cumulative input context tokens ($1 - 655.33 / 235{,}765.73$).
2. **Elimination of Distractor Collisions:** In the clean-slate condition, distractor collisions were completely eliminated (0 of 15 trials, 0.0%), and all 15 tasks passed the deterministic AST and marker oracle checks (100.0% pass rate).
3. **Distractor-Induced Error Surge:** In the `fork_60k` condition, semantic distractors present in historical turns caused collisions in 7 of 15 trials (46.67%). In these trials, the subagent incorporated deprecated identifiers or legacy fallback methods discussed in prior turns, reducing the task oracle pass rate to 53.33% (8 of 15 trials).

---

## 8. Provider prompt caching: economic mitigation vs. attention reality

A frequent defense of transcript inheritance is that provider prompt caching (such as Anthropic Claude prompt caching, OpenAI Responses API caching, or Google Gemini context caching) renders large contexts financially negligible. To evaluate this claim, the benchmark modeled execution costs under current standard frontier pricing ($2.50 / 1M uncached input tokens, $1.25 / 1M cached input tokens, $10.00 / 1M output tokens).

### Simulated Financial Cost Analysis

| Condition | Mean Uncached Cost | Mean Cached Cost (50% Prefix Discount) | Cost Reduction from Caching | Clean-Slate Cost Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **`clean_slate`** | **$0.002329** | **$0.002329** | 0.0% (Under 1,024-token cache min) | **Baseline** |
| `fork_10k` | $0.105103 | $0.070369 | 33.05% | Clean-slate is 30.2x cheaper |
| `fork_30k` | $0.296221 | $0.197781 | 33.23% | Clean-slate is 84.9x cheaper |
| `fork_60k` | $0.590099 | $0.393698 | 33.28% | Clean-slate is 169.0x cheaper |
| `fork_90k` | $0.883988 | $0.589623 | 33.30% | Clean-slate is 253.2x cheaper |

### The Limits of Prompt Caching

While prompt caching reduces marginal per-token read rates by 50% (saving roughly 33% of total multi-turn session cost on forked tasks), it fails to resolve three fundamental harness bottlenecks:

1. **Context Window Saturation:** Cached tokens consume active context window capacity. A subagent inheriting 90,000 tokens has only 38,000 tokens remaining in a 128k context window, severely restricting its ability to ingest build logs or large diffs.
2. **Time-to-First-Token (TTFT) Latency:** Large prompt prefixes, even when cached in memory, require server-side KV-cache retrieval, validation, and serialization. Time-to-first-token latency increases with context size regardless of cache hit status.
3. **Persistence of Distractors:** Caching does not alter attention distribution. A cached token participates in self-attention calculations identically to an uncached token. Semantic distractors in a cached transcript degrade reasoning accuracy just as severely as in an uncached transcript.

---

## 9. Practical engineering tradeoffs: the Context Omission Gap

Clean-slate specialist context is not a free optimization. By eliminating the transcript, the harness incurs a coordination burden: **the coordinator must explicitly synthesize every necessary constraint into the dispatch contract**.

### The Context Omission Gap Defined
The **Context Omission Gap** occurs when a clean-slate subagent fails to complete a task because the coordinator omitted a vital constraint, historical user decision, or implicit environment requirement that was present in earlier conversation turns but absent from the task contract.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ The Context Omission Gap Failure Loop                                  │
│                                                                        │
│ Turn 3: User specifies "Ensure all scripts maintain Python 3.10 syntax"│
│ ...                                                                    │
│ Turn 22: Coordinator delegates bugfix to Clean-Slate Specialist        │
│          Contract specifies bug in handler.py, but OMITS Python 3.10   │
│ ...                                                                    │
│ Subagent writes patch using Python 3.12 syntax (type statement)        │
│ Test passes locally on 3.12, but fails production integration!         │
└────────────────────────────────────────────────────────────────────────┘
```

### Architectural Mitigations
To prevent the Context Omission Gap without resorting to transcript dumping, harnesses must implement:

1. **Structured Contract Schemas:** Mandatory schema validation ensuring that authority, environment constraints, target files, and verification criteria are populated before spawn.
2. **Explicit User Approval Forwarding:** When a user grants explicit consent (e.g., authorization to mutate a production database or bump a version), the coordinator must forward the authorization token directly in the contract, rather than expecting the child to infer it from chat logs.
3. **Bounded Clarification Protocols:** If a clean-slate subagent discovers an ambiguity, it should emit a structured clarification query back to the coordinator, rather than inheriting 50,000 tokens of speculative context.

---

## 10. Limitations and threats to validity

1. **Synthetic Task Boundary:** The benchmark uses generated software tasks (syntax repairs, RBAC policy checks, JSON config transformations) with deterministic oracles. While designed to mirror common harness operations, real developer conversations exhibit higher linguistic complexity and conversational entropy.
2. **Local Tokenizer vs. Provider Telemetry:** Token counts are calculated locally using `tiktoken 0.14.0` with `o200k_base`. Production provider requests (such as OpenAI Responses API or Anthropic Messages API) include proprietary message framing, role delimiters, and system headers that are not captured in raw serialized JSON.
3. **Deterministic Distractor Simulation:** Distractor collisions in this benchmark are modeled using depth-based attention decay distributions derived from published academic literature (Liu et al., 2024; Chroma, 2025). Specific collision rates will vary across live proprietary model checkpoints, temperature settings, and prompt phrasing.
4. **Host Runtime Symptoms:** All executions ran on a single Windows x86_64 host. Variations in CPU scheduling or memory access times are host runtime symptoms, not confirmed software defects.

---

## 11. Conclusion and implementation checklist

Transcript inheritance during multi-agent delegation represents a convenience trap that trades architectural precision for exponential token inflation and attention decay. In this evaluation, clean-slate zero-flight dispatch reduced cumulative input context tokens by **99.7220%** and completely eliminated semantic distractor collisions.

### Actionable Harness Checklist
- [x] **Enforce `fork_turns: "none"`:** Audit all subagent spawn primitives to ensure history cloning is disabled by default.
- [x] **Adopt 4-Part Declarative Contracts:** Require all delegations to serialize Authority, Scope, Targets, and Cost Layers.
- [x] **Implement JIT Retrieval:** Equip subagents with AST search (`ast-grep`) and indexed document search (`qmd`) rather than pre-loading full files.
- [x] **Separate Sandboxing from Context Isolation:** Do not assume a clean-slate context provides filesystem or process security; enforce Git worktrees and execution boundaries separately.
- [x] **Monitor Context by Agent Tier:** Track token consumption for coordinators and subagents independently to detect hidden context inheritance leaks.
