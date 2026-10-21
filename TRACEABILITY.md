# Evidence Traceability Matrix

This document maps all headline empirical claims and quantitative measurements reported in whitepapers in this repository to their local source metric files.

## Benchmark Isolation Architecture

In `koality-whitepapers`, benchmark evaluations and integrity manifests are intentionally self-contained within each paper's `supporting/benchmark/` directory. Each study maintains its own pinned dependencies, synthetic fixtures, hash manifests, and raw trial metrics to ensure independent reproducibility and immutability without external dependencies on other repositories (such as `ai-research-and-benchmarks`).

---

## 1. Clean-Slate Specialist Context

**Paper:** [`papers/AI-Engineering/clean-slate-specialist-context/PAPER.md`](papers/AI-Engineering/clean-slate-specialist-context/PAPER.md)  
**Primary Source:** [`papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/metrics/summary.json`](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/metrics/summary.json)  
**Trial Log:** [`papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/metrics/trial-metrics.json`](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/metrics/trial-metrics.json)

| Headline Metric / Claim | Paper Value | Source JSON Field | Source Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| Cumulative token reduction vs. 60k baseline | 99.7220% | `key_findings.token_reduction_vs_fork_60k_pct` | 99.722 | Verified |
| Clean-slate mean cumulative input tokens | 655.33 | `by_condition.clean_slate.mean_cumulative_input_tokens` | 655.33 | Verified |
| Inherited 60k baseline mean input tokens | 235,765.73 | `by_condition.fork_60k.mean_cumulative_input_tokens` | 235765.73 | Verified |
| Clean-slate oracle pass rate | 100.0% (15/15) | `by_condition.clean_slate.oracle_pass_rate_pct` | 100.0 | Verified |
| Clean-slate distractor collision rate | 0.0% (0/15) | `by_condition.clean_slate.distractor_collision_rate_pct` | 0.0 | Verified |
| Fork 60k distractor collision rate | 46.67% (7/15) | `by_condition.fork_60k.distractor_collision_rate_pct` | 46.67 | Verified |
| Fork 60k oracle pass rate | 53.33% (8/15) | `by_condition.fork_60k.oracle_pass_rate_pct` | 53.33 | Verified |
| Total trials evaluated | 75 | `total_trials` | 75 | Verified |
| Task variants evaluated | 15 | `task_variants` | 15 | Verified |

---

## 2. Context Efficiency in Agent Harnesses

**Paper:** [`papers/AI-Engineering/context-efficiency-methods/PAPER.md`](papers/AI-Engineering/context-efficiency-methods/PAPER.md)  
**Component A Source (Headroom):** [`papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/metrics/summary.json`](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/metrics/summary.json)  
**Components B–E Source (Tooling Suite):** [`papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/metrics/tooling-suite-results.json`](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/metrics/tooling-suite-results.json)

| Headline Metric / Claim | Paper Value | Source JSON File | Source JSON Field | Source Value | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Headroom mean token reduction | 86.53% | `summary.json` | `overall.mean_headroom_tokens_saved_pct` | 86.53 | Verified |
| Headroom marker survival | 25/25 (100.0%) | `summary.json` | `overall.gold_markers_found` / `gold_markers_total` | 25 / 25 | Verified |
| Build log output token reduction | 97.52% | `summary.json` | `categories.build_log_output.mean_headroom_tokens_saved_pct` | 97.5222 | Verified |
| Grep hit output token reduction | 97.16% | `summary.json` | `categories.grep_hit_output.mean_headroom_tokens_saved_pct` | 97.1585 | Verified |
| JSON tool output token reduction | 64.91% | `summary.json` | `categories.json_tool_output.mean_headroom_tokens_saved_pct` | 64.9091 | Verified |
| QMD lexical top-1 accuracy | 4/4 | `tooling-suite-results.json` | `qmd.top_1_correct` | "4/4" | Verified |
| QMD mean source byte reduction | 80.97% | `tooling-suite-results.json` | `qmd.mean_selected_source_reduction_percent` | 80.9652 | Verified |
| QMD full fixture corpus size | 746 bytes | `tooling-suite-results.json` | `qmd.queries[0].full_fixture_corpus_bytes` | 746 | Verified |
| ast-grep selected function size | 282 bytes | `tooling-suite-results.json` | `ast_grep.result.selected_bytes` | 282 | Verified |
| ast-grep fixture file size | 758 bytes | `tooling-suite-results.json` | `ast_grep.result.source_bytes` | 758 | Verified |
| ast-grep byte reduction | 62.80% | `tooling-suite-results.json` | `ast_grep.result.byte_reduction_percent` | 62.7968 | Verified |
| ast-grep marker retention | 3/3 | `tooling-suite-results.json` | `ast_grep.result.gold_markers_retained` | "3/3" | Verified |
| Trafilatura mean byte reduction | 85.86% | `tooling-suite-results.json` | `webfetch.mean_byte_reduction_percent` | 85.8605 | Verified |
| Trafilatura marker retention | 15/15 | `tooling-suite-results.json` | `webfetch.gold_markers_retained` | "15/15" | Verified |
| Static prompt shared prefix | 216 bytes | `tooling-suite-results.json` | `prompt_prefix.result.declared_static_prefix_bytes` | 216 | Verified |

---

## 3. Encrypted Reveal Envelopes and Local Secret Use

- **Paper:** [`papers/AI-Engineering/zero-plaintext-vault-reveal/PAPER.md`](papers/AI-Engineering/zero-plaintext-vault-reveal/PAPER.md)
- **Primary source:** [`papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark/metrics/summary.json`](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark/metrics/summary.json)
- **Trial log:** [`papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark/metrics/trial-metrics.json`](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark/metrics/trial-metrics.json)

| Headline Metric / Claim | Paper Value | Source JSON Field | Source Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| Synthetic fixtures evaluated | 5 | `total_fixtures_evaluated` | 5 | Verified |
| Constructed response, tool-result, replacement, and prompt-history checks | 5/5 each | `boundary_pass_rates` | 5/5 each | Verified; modeled checks only |
| Literal sentinel appearances in authored histories | 8 naive / 0 sandbox-shaped | `sentinel_leakage_counts.*literal_sentinel_appearances` | 8 / 0 | Verified |
| Raw credential appearances in authored histories | 10 naive / 0 sandbox-shaped | `sentinel_leakage_counts.*raw_credential_appearances` | 10 / 0 | Verified |
| Mean cumulative input tokens | 326.6 naive / 193.8 sandbox-shaped | `token_consumption_comparison.mean_*_cumulative_input_tokens` | 326.6 / 193.8 | Verified |
| Token reduction | 35.26% unweighted mean by fixture; 40.66% between displayed means | `token_consumption_comparison.*reduction_percentage` | 35.26% / 40.66% | Verified; distinct aggregations |
| Python string-replacement input | 50 KiB synthetic UTF-8 | `cryptographic_microbenchmarks[python_string_replacement_50kib_log].details` | exactly 50 KiB | Verified; not MCP scrubber timing |

The Python runner uses a prewarmed tokenizer cache and rejects cache-miss downloads. These values describe constructed Python data; they are not runtime containment results.
