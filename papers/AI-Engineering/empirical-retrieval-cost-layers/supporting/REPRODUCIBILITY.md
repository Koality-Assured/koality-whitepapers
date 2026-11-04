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
- **Network Access:** Zero external network calls. All retrieval and benchmark tests execute locally against local repository files and SQLite indexes.

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

Execute the standalone evaluation script to reproduce single-turn and cumulative 10-turn token metrics across the 5 canonical scenarios:

```bash
python supporting/benchmark/run_benchmark.py
```

Expected output:
- **Arm A Single-Turn Context:** ~29,662 tokens
- **Arm B Single-Turn Context:** ~11,746 tokens
- **Mean Token Reduction:** ~60.40%
- **Cumulative 10-Turn Tokens Saved:** ~179,160 tokens
- **Monetary Savings (Claude 3.5/5.5 Sonnet):** ~92.48%

### Step 2: Reproduce Retrieval Accuracy & Latency (QMD Suite)

To reproduce the Mean Reciprocal Rank (MRR), Precision@1, and batch speedup factor:

```bash
python scripts/benchmarks/benchmark_retrieval.py --mode search --with-multi-get
```

Expected output:
- **Mean Reciprocal Rank (MRR):** $\ge 0.90$ (measured: 0.9286)
- **Precision@1:** $\ge 80.0\%$ (measured: 85.7%)
- **Average BM25 Search Latency:** $\le 250\text{ ms}$ (measured: 220.3ms)
- **Batch Multi-Get Speedup:** $\ge 4.0\text{x}$ (measured: 5.27x over serial retrieval)

### Step 3: Verify AST Symbol Extraction Savings

To reproduce the concrete syntax tree token savings using `ast-grep`:

```bash
python scripts/cost-layers/validate_ast_grep.py
```

Expected output:
- Python script symbol extraction savings: $\ge 90.0\%$ (measured: 93.3%)
- Frontmatter and YAML extraction savings: $\ge 90.0\%$ (measured: 91.5%–94.5%)
