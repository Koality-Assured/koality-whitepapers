# Reproducibility guide: Clean-slate specialist context benchmark

This guide provides instructions for independently reproducing the empirical results presented in [PAPER.md](../PAPER.md) and verifying the integrity of the synthetic benchmark package.

## 1. System prerequisites

The benchmark runs completely offline with zero network requests or provider API keys.

- **Python Runtime:** CPython 3.13.16 (x86_64)
- **Package Manager:** `uv 0.12.23`
- **Supported Platforms:** Windows x86_64 (evidence host), Linux x86_64, macOS arm64/x86_64

## 2. Directory structure

All benchmark assets reside within `papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/`:

```text
benchmark/
├── pyproject.toml              # Project definition pinning tiktoken==0.14.0
├── uv.lock                     # Lockfile fixing exact package digests
├── fixtures.py                 # Deterministic synthetic task and distractor generator
├── run_benchmark.py            # Offline benchmark runner measuring o200k_base tokens
├── METHOD.md                   # Formal methodology specification
├── method-manifest.json        # Structured experimental scope and parameters
├── run-manifest.json           # Execution record and runtime configuration
├── sha256-manifest.json        # Normalized-text digests for all package files
├── verify_sha256_manifest.py   # Script validating normalized-text SHA-256 hashes
└── metrics/
    ├── summary.json            # Aggregated token counts, pass rates, and cost models
    └── trial-metrics.json      # 75 individual trial measurement records
```

## 3. Step-by-step execution

### Step A: Verify Package Integrity Before Execution
From the `supporting/benchmark/` directory, verify that no package files have been tampered with or corrupted:

```bash
python verify_sha256_manifest.py --manifest sha256-manifest.json
```
*Expected Output:*
```text
Verified 10 files in sha256-manifest.json using normalized-text SHA-256.
```

### Step B: Sync Locked Dependencies
Install pinned dependencies directly from the checked-in `uv.lock`:

```bash
uv sync --locked --python 3.13.16
```

### Step C: Execute Benchmark Suite
Run the 75-trial benchmark suite:

```bash
uv run --locked python run_benchmark.py
```
*Expected Terminal Output:*
```text
Starting Clean-Slate Context Benchmark (tiktoken 0.14.0, o200k_base)...
Generated 15 task contracts across 3 archetypes.
Executed 75 trials in ~1.3 seconds.
Saved 75 trial rows to trial-metrics.json
Saved summary metrics to summary.json
Clean-Slate Mean Tokens: 655.33 vs Fork-60k: 235765.73 (99.722% reduction)
Clean-Slate Pass Rate: 100.0% vs Fork-60k: 53.33%
```

### Step D: Re-Verify Checksums
Re-run the verification script to confirm that outputs match the checked-in digests:

```bash
uv run --locked python verify_sha256_manifest.py
```

## 4. Line-Ending Normalization Protocol

To guarantee cross-platform hash consistency between Windows (CRLF) and POSIX (LF) environments, `verify_sha256_manifest.py` applies the following rule:
- All `\r\n` and bare `\r` byte sequences are normalized to `\n` prior to calculating SHA-256 digests.
- This ensures bit-for-bit identical hashes across Git checkouts regardless of `core.autocrlf` configuration.

## 5. Output Data Interpretation

The runner generates two JSON files in `metrics/`:
1. **`summary.json`:** Contains high-level aggregates for each of the five evaluated context conditions (`clean_slate`, `fork_10k`, `fork_30k`, `fork_60k`, `fork_90k`), including mean cumulative tokens, median tokens, oracle pass rates, distractor collision rates, and modeled API costs.
2. **`trial-metrics.json`:** Contains the 75 granular trial rows, detailing per-turn input tokens (`turn_1_input_tokens`, `turn_2_input_tokens`, `turn_3_input_tokens`), assistant output tokens, oracle pass status, and collision flags.
