# Reproducibility guide: Commit-Bound Proof Gates

This guide documents how to verify the offline proof-gate suite, routing benchmark, SHA-256 integrity manifest, candidate `proof.schema.json`, and seeded-defect fixture reproductions reported in [PAPER.md](../PAPER.md).

## 1. Environment

The canonical benchmark artifacts were generated on:

- **OS:** Windows 10 (`AMD64`)
- **Python:** `3.11.9` (standard library only; zero third-party `pip` dependencies required)
- **Git:** `git version 2.49.0.windows.1`
- **Additional runtimes for blind-trial fixture reproduction (optional):** Go `1.21+` and Node.js `v24.19.0`
- **Network access:** None. All benchmark and unit tests run offline using temporary Git repositories.

## 2. Directory structure

```text
papers/AI-Engineering/commit-bound-proof-gates/
├── PAPER.md
└── supporting/
    ├── CLAIM-TO-EVIDENCE.md
    ├── REPRODUCIBILITY.md
    ├── SOURCES.md
    ├── proof.schema.json
    ├── diagrams/
    │   ├── README.md
    │   ├── 01-promotion-gate-topology.mmd
    │   ├── 02-commit-invalidation-sequence.mmd
    │   └── 03-negative-routing-boundary.mmd
    └── benchmark/
        ├── proof_gate.py
        ├── synthetic_repos.py
        ├── run_benchmark.py
        ├── test_proof_gate.py
        ├── verify_sha256_manifest.py
        ├── sha256-manifest.json
        ├── metrics/
        │   ├── summary.json
        │   ├── trial-metrics.json
        │   ├── routing-metrics.json
        │   ├── blind-trial-results.json
        │   └── matrix.csv
        └── blind-trials/
            ├── PROTOCOL.md
            ├── ground-truth-rubric.json
            ├── fixtures/
            └── packets/
```

## 3. Reproduction steps

### Step 1: Verify normalized-text SHA-256 integrity

From the paper directory (`papers/AI-Engineering/commit-bound-proof-gates/`):

```bash
python supporting/benchmark/verify_sha256_manifest.py
```

Expected output: `Verified 28 files in sha256-manifest.json using normalized-text SHA-256.`

### Step 2: Run the unit and matrix test suite

```bash
python -m unittest discover -s supporting/benchmark -p "test_*.py" -v
```

Expected result: all tests pass (`OK`), exercising the 31 proof-gate scenarios, the ancestry-only trailing-commit ablation, the 16 negative-routing samples, and `supporting/proof.schema.json` contract alignment.

### Step 3: Re-run the 10-iteration benchmark into a temporary directory

```bash
python supporting/benchmark/run_benchmark.py --iterations 10 --out /tmp/proof-gate-repro
```

Expected aggregate metrics:

- `naive_status_only`: 29.03% accuracy, 21.43% fail-closed rate, 78.57% false-accept rate
- `ancestry_only`: 74.19% accuracy, 71.43% fail-closed rate, 28.57% false-accept rate
- `strict_commit_bound`: 100.00% accuracy, 100.00% fail-closed rate, 0.00% false-accept rate
- `deterministic_boundary` routing classifier: 100.00% accuracy (`16/16`), 0.00% over-escalation, 0.00% under-escalation

Note: Wall-clock milliseconds (`p50`, `mean`, `p95`, `max`) vary across CPU, filesystem speed, and OS process creation overhead.

### Step 4: Reproduce the four seeded defects (optional multi-language check)

Each fixture in `supporting/benchmark/blind-trials/fixtures/` passes its happy-path unit test and deterministically fails its seeded-defect reproduction assertion:

```bash
# 1. Go race/lease TOCTOU (CWE-362)
cd supporting/benchmark/blind-trials/fixtures/trial_01_race_lease_go && go test -v ./...

# 2. Python stale-SHA / symbolic ref bypass (CWE-345)
cd supporting/benchmark/blind-trials/fixtures/trial_02_stale_sha_gate_py && python -m unittest test_repro.py -v

# 3. Node.js sibling-prefix path escape (CWE-22)
cd supporting/benchmark/blind-trials/fixtures/trial_03_path_boundary_js && node --test exporter.test.mjs

# 4. Python fail-open exception swallow (CWE-636)
cd supporting/benchmark/blind-trials/fixtures/trial_04_silent_error_swallow_py && python -m unittest test_repro.py -v
```
