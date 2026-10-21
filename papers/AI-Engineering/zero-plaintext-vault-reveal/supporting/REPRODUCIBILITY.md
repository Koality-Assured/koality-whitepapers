# Reproducibility guide: Zero-Plaintext Agent Context Canary Benchmark

This guide documents the Python simulation, its pinned tokenizer dependency, and the steps to reproduce its modeled results. The runner does not execute the `llm-vault` or `llm-vault-mcp` implementations.

---

## 1. Evaluation environment

The checked-in benchmark run was executed on the host recorded in `metrics/summary.json`. Reproduce it with:

- **OS:** `Windows-10-10.0.26200-SP0` as reported by Python `platform.platform()`
- **Runtime:** Python 3.11.9 (CPython x86_64)
- **Tokenizer Package:** `tiktoken` 0.14.0 (`o200k_base` encoding)
- **Network scope:** The runner uses a prewarmed local tokenizer cache and rejects cache-miss downloads. No network monitoring was used; the cache-miss guard is enforced in code.

---

## 2. Directory structure

```text
papers/AI-Engineering/zero-plaintext-vault-reveal/
├── PAPER.md
└── supporting/
    ├── CLAIM-TO-EVIDENCE.md
    ├── SOURCES.md
    ├── REPRODUCIBILITY.md
    └── benchmark/
        ├── fixtures.py
        ├── pyproject.toml
        ├── run_benchmark.py
        ├── run-manifest.json
        ├── sha256-manifest.json
        ├── verify_sha256_manifest.py
        └── metrics/
            ├── summary.json
            └── trial-metrics.json
```

---

## 3. Reproduction steps

### Step 1: Verify file integrity

Before executing the benchmark, verify that no package files have been modified using the SHA-256 manifest:

```bash
cd papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark
python verify_sha256_manifest.py
```

Expected output (timings and environment metadata vary by host):
```text
Integrity check passed! 7 files verified against SHA-256 manifest.
```

### Step 2: Set up Python virtual environment

Install the required tokenizer dependency using `uv` or standard `pip`:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

python -m pip install "tiktoken==0.14.0"
```

### Step 3: Preload the tokenizer data

The first `o200k_base` initialization downloads the public tokenizer rank file into tiktoken's cache. Do this setup step while network access is available; the benchmark runner itself refuses to fetch the file:

```bash
python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"
```

### Step 4: Execute the canary benchmark

Run the automated benchmark runner:

```bash
python run_benchmark.py
```

Expected output:
```text
Benchmark status: PASS
Simulated boundary rates: ...
Summary written to .../metrics/summary.json
```

---

## 4. Metric assertions

The runner models 5 synthetic fixtures across 4 constructed boundaries. It uses only a prewarmed local tokenizer cache during execution and refuses a cache-miss download. These Python checks do not exercise HTTP responses, MCP JSON-RPC calls, subprocesses, or an LLM runtime:
1. **API-shaped JSON:** The fixture creates a dictionary representing an encrypted response and checks it for the raw synthetic value.
2. **MCP-shaped result:** Python replacement is applied to constructed stdout and stderr strings before serializing a mock tool result.
3. **Variant replacement:** Python `str.replace` is applied to a synthetic log containing selected fixture variants.
4. **Constructed prompt history:** The runner compares explicitly authored naive and sandbox JSON histories.

### Summary metrics from the current run:
- Literal sentinel and raw credential appearances are reported separately in `metrics/summary.json`; some sentinels are substrings of their synthetic credentials.
- Both counts are zero in the constructed sandbox history.
- Mean Cumulative Input Tokens (Naive): **326.6**
- Mean Cumulative Input Tokens (Sandbox): **193.8** (35.26% unweighted mean of per-fixture reductions; 40.66% reduction between the displayed means)
- Python `str.replace` timing on a 50 KiB UTF-8 string: see `cryptographic_microbenchmarks`; this is not MCP scrubber latency.
- PBKDF2, scrypt, and HMAC entries use Python standard-library implementations; they are not timing measurements of the TypeScript client or Node.js server.
