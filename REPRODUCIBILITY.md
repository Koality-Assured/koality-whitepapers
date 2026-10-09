# Reproducibility manifest

## Evidence run

- Run timestamp recorded in benchmark/run-manifest.json: 2026-10-09T22:36:57Z.
- Platform recorded: Windows x86_64.
- Trials: 15 fixed synthetic fixtures, five in each of three categories.
- Provider API calls: zero.
- Replay status: the evidence run completed once; no independent replay is recorded.
- Run identity: bound to the public package files and 15 serialized input/output hashes in benchmark/run-manifest.json. No external repository revision is required.

## Pinned environment

| Component | Version or setting | Evidence |
| --- | --- | --- |
| CPython | 3.13.16 | benchmark/method-manifest.json and benchmark/run-manifest.json |
| uv | 0.12.23 | benchmark/method-manifest.json and benchmark/run-manifest.json |
| Headroom AI | 0.40.0 | benchmark/pyproject.toml and benchmark/uv.lock |
| tiktoken | 0.14.0 | benchmark/pyproject.toml and benchmark/uv.lock |
| Tokenizer | o200k_base | benchmark/method-manifest.json and runner mapping check |
| Trafilatura | 2.3.1, not imported | Reused lock environment |
| Lock records | 108, including a virtual local project entry | benchmark/run-manifest.json |

The lock hashes downloadable dependency artifacts. The virtual local project record has no package artifact hash. The gpt-4o string selects Headroom's local counting path; it does not call a provider model. The fixtures use deterministic source templates without a random-number generator.

## Public files and SHA-256

The benchmark SHA manifest is benchmark/sha256-manifest.json. It covers:

| File | SHA-256 |
| --- | --- |
| benchmark/METHOD.md | 48373cbd309be9cfbaf9597f1a1cdcb660af50e1f6916c68cd66f632894372da |
| benchmark/fixtures.py | d3a4d0d77e5444c8566a3091a555a9c4460e18a48031bc632d2babf3a7ca2f57 |
| benchmark/method-manifest.json | 0d2ae63787f7ae692991ad655c136e67e5285fd48e068e00817bb7c423f6532e |
| benchmark/metrics/summary.json | ca19d33ad023014daff68905f3d770e49f3bd40020491de8d90d7b8ad872b98e |
| benchmark/metrics/trial-metrics.json | 07a060d265fc65dc8d42d9acc06f51af0d4fb48cde322d8c418c9901d44a5789 |
| benchmark/pyproject.toml | d05c379288ab9b4a7c263fb634e6b9b74c5fee8311740c3abb9cd2a0a4fcbfe9 |
| benchmark/run-manifest.json | c0ac0ac3a7b1338b97039670800fb49cad45e240c4dc1e03beb7cb02eda19aa8 |
| benchmark/run_benchmark.py | 4ceb4db9ca1967f5bb40c5170253c4112156ff7adedcd6d92165d5a1a3f6c88d |
| benchmark/uv.lock | c9577034979151b56d423bfe9d3570c3e58931a768be3b5141385384ce6573d7 |

The run manifest includes the recorded hashes of the 15 case inputs and outputs. The SHA manifest covers run-manifest.json but does not hash itself. The reviewer checked listed artifact hashes against package bytes and matched each recorded input/output digest pair to its metric row. Serialized trial payloads are omitted, so those hashes were not recomputed from payload bytes; this is a consistency check, not an independent replay.

SHA-256 of benchmark/sha256-manifest.json: 955725238e32dcd2fa8bb50b651ff7fc046f6617f7325b6da540319973c94a76.

## Rerun

From the benchmark directory, use CPython 3.13.16 and uv 0.12.23:

    uv sync --locked --python 3.13.16
    uv run --locked python run_benchmark.py --output-dir output

The command reads only the package's fixture generator and locked environment. It writes full synthetic inputs and compressed outputs under output/trial-details.jsonl, per-trial metrics, an aggregate, and environment metadata. The generated content is synthetic and matches the public fixture generator.

The evidence files support recomputation of the reported aggregates. Because no independent replay has been recorded, the paper makes no claim that a second run reproduced the evidence output.
