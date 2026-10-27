# Reproducibility guide: Precision-First Context Scrubbing Benchmark

This guide describes how to run the benchmark from a clean checkout of the published `koality-whitepapers` repository. Results are synthetic fixture measurements, not a test of live personal data or agent task quality.

## 1. Recorded environment

The checked-in metric snapshot reports platform `Windows-10-10.0.26200-SP0`, CPython 3.11.9, `tiktoken` 0.14.0, and the pinned scanner source commit listed in `run-manifest.json`. Timings vary by hardware and runtime. The runner does not make live provider API calls; pip may need network access to install dependencies, and `tiktoken` may retrieve its encoding data on first use.

## 2. Package contents

The benchmark directory includes the labeled corpus, workload generator, runner, pinned Python requirements, generated metric snapshots, hash verifier, and the scanner's `src/pii_scan/` source snapshot with its upstream MIT license. The scanner snapshot is pinned to commit `514f708e8890add75a963ff771245c1256394323` and listed in `run-manifest.json`.

The upstream source's direct pip installation was tested and failed during wheel metadata preparation because Hatchling attempted to add `pii_scan/data/__init__.py` to the wheel archive twice. `SOURCES.md` records the exact command and error. The vendored source is a bounded workaround for running this benchmark only; it does not repair upstream packaging or imply that installing the upstream project succeeds. No scanner-repository files are modified by this package.

## 3. Reproduction steps

After the publication commit is available in the public repository, clone it and enter the benchmark directory:

```bash
git clone https://github.com/Koality-Assured/koality-whitepapers.git
cd koality-whitepapers/papers/AI-Engineering/precision-first-context-scrubbing/supporting/benchmark
python -m venv .venv
```

Activate the environment (`.venv\\Scripts\\activate` in Windows Command Prompt or `source .venv/bin/activate` on macOS/Linux), then install the pinned dependencies and run the checks:

```bash
python -m pip install -r requirements.txt
python verify_sha256_manifest.py
python -B run_benchmark.py
python verify_sha256_manifest.py
```

The runner regenerates `metrics/summary.json`, `metrics/trial-metrics.json`, `run-manifest.json`, and `sha256-manifest.json`. A subsequent integrity check verifies the generated files against the newly written normalized-text hashes. The first check verifies the checked-in snapshot before running it.

## 4. Interpreting the recorded results

The recorded corpus contains 101 labeled cases: 13 documented fake Stripe card format markers, 3 MAC format markers from the IANA documentation-use range, and 85 negative controls. The positive labels mean format recognition only; they do not identify live personal data. No positive SSN, email, IPv4, or IPv6 cases are included, so recall for those categories is undefined.

In the checked-in run, aggregate deterministic precision/recall were 0.8889/0.5000 (8 true positives, 1 false positive, 8 false negatives); the simple regex baseline measured 0.2581/1.0000 (16 true positives, 46 false positives, 0 false negatives). On a separate five-file all-negative workload, the baseline emitted 17 findings and 912 JSON tokens; the deterministic scanner emitted no findings and 1 JSON token. This output-size comparison does not measure full prompt size, agent reasoning, task quality, or repository-scale savings.

The same run measured 6,253.6 lines/second over 10,000 generated lines, a 7.48 ms scan call for a 100-line input, and a 46.656 ms scan call that skipped one 24 KB overlength line. These are single-run environment observations. The benchmark does not run an unbounded or adversarial regex and does not measure or establish ReDoS resistance.
