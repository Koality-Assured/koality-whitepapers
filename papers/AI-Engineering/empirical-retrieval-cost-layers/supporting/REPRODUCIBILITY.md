# Reproducibility guide: Empirical Retrieval Cost Layers

This guide documents the execution environment, test procedures, and verification commands required to reproduce the empirical results reported in [PAPER.md](../PAPER.md).

---

## 1. Evaluation environment

The canonical benchmark run was executed on Windows x86_64 under the following pinned environment:

- **OS:** Windows 11 (build 10.0.26200)
- **CPU:** AMD64 Architecture (x86_64)
- **Runtime:** Python 3.11.9 (CPython x86_64)
- **CLI Tools:**
  - `qmd` 2.8.3 (local SQLite + BM25 + GGUF engine)
  - `ast-grep` 0.45.3
  - `git` 2.47+
- **Source corpus:** Public `Koality-Assured/ai-router` checkout at the benchmark's source revision; the benchmark does not inspect private repositories.
- **Network Access:** The benchmark itself makes zero external network calls. Clone or fetch the public source checkout separately, then run the benchmark locally against that checkout and its detached QMD index.

---

## 2. Directory structure

```text
papers/AI-Engineering/empirical-retrieval-cost-layers/
├── PAPER.md
└── supporting/
    ├── CLAIM-TO-EVIDENCE.md
    ├── SOURCES.md
    ├── REPRODUCIBILITY.md
    └── benchmark/
        ├── run_benchmark.py
        └── metrics/
            ├── summary.json
            └── trial-metrics.json
```

---

## 3. Reproduction steps

### Step 1: Run the Comparative Evaluation (Arm A vs. Arm B)

Run the evaluation script against a local checkout of the public `Koality-Assured/ai-router` source corpus. The source checkout is explicit because this whitepaper repository does not contain the corpus used by the scenarios:

```bash
python supporting/benchmark/run_benchmark.py --source-root /path/to/ai-router --out /path/to/output
```

This runner measures the Arm A versus Arm B payload comparison with `qmd search` and bounded `qmd multi-get`; it does not execute `ast-grep`. The AST fixture measurements cited by the paper are reproduced from the separate public report in Step 3.

Expected output:
- **Arm A Single-Turn Context:** ~29,662 tokens
- **Arm B Single-Turn Context:** ~11,746 tokens
- **Mean Token Reduction:** ~60.40%
- **Cumulative 10-Turn Tokens Saved:** ~179,160 tokens
- **Provider billing/cache hits:** Not measured; use provider-specific usage telemetry for any cost study.

### Step 2: Reproduce Retrieval Accuracy & Latency (QMD Suite)

The paper also cites retained public reports for QMD retrieval quality and latency:

```bash
https://github.com/Koality-Assured/ai-router/blob/main/results/reports/analysis/qmd-suite-benchmark/2026-10-29/benchmark-report.md
```

The cited QMD suite reports 0.2025s BM25 search, 10.293s dense search, and 0.1893s batch retrieval versus 0.4006s for two serial calls. The cited multi-trial report records Fleet MRR 0.9062, Precision@1 81.2%, and p50 search latency 187.77ms.

### Step 3: Review AST Symbol Extraction Savings

The AST-grep measurements are retained in the cited public multi-trial report rather than represented as a runnable script in this repository:

```text
https://github.com/Koality-Assured/ai-router/blob/main/results/cost-layers/combined/2026-10-08/report.md
```

That report records estimated savings of 93.3% for Python scripts, 90.5% for agent-card YAML, and 94.5% for skill frontmatter. Re-running those fixtures requires the public ai-router benchmark scripts and their source corpus.
