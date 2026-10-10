# Reproducibility manifest

Paths in this guide are relative to this `supporting/` directory unless stated otherwise. File paths inside the benchmark manifests are relative to the `benchmark/` package directory.

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

The benchmark SHA manifest is `benchmark/sha256-manifest.json`. Hashes are over normalized text bytes: the verifier reads each listed file as bytes, converts CRLF and bare CR line endings to LF, then computes SHA-256. The manifest excludes itself; its normalized digest is listed after the table. This procedure makes the published values stable on Windows checkouts that use CRLF. The run manifest declares the same normalization for its nested artifact digests.

Run `python verify_sha256_manifest.py` from `benchmark/` to check the Headroom package manifest. The verifier rejects missing files, path traversal, malformed digests, and mismatches.

| File | Normalized-text SHA-256 |
| --- | --- |
| benchmark/METHOD.md | e58f7258214368c7ec243798488c937a7d20b484522720caaa5cafba970b137b |
| benchmark/fixtures.py | d3a4d0d77e5444c8566a3091a555a9c4460e18a48031bc632d2babf3a7ca2f57 |
| benchmark/method-manifest.json | e65240d14872efadf68aee7589a4077b97b27a32cf71fa48dcd5ba263cb053ca |
| benchmark/metrics/summary.json | a401f1d51ca9bdcc6ff267793d525d2b853371494e4baffb8be5c04103c89c66 |
| benchmark/metrics/trial-metrics.json | a97f37c5c70797b61edd849d6e11b59af375a4656af764b5b814942c450cc790 |
| benchmark/pyproject.toml | d05c379288ab9b4a7c263fb634e6b9b74c5fee8311740c3abb9cd2a0a4fcbfe9 |
| benchmark/run-manifest.json | 8bd7541b34b3cfd2e77e0d710a26c65387c0a68133387afe7ec83b94a09d239c |
| benchmark/run_benchmark.py | 4ceb4db9ca1967f5bb40c5170253c4112156ff7adedcd6d92165d5a1a3f6c88d |
| benchmark/uv.lock | c9577034979151b56d423bfe9d3570c3e58931a768be3b5141385384ce6573d7 |
| benchmark/verify_sha256_manifest.py | 3c4ab8f99cd1ef9bc7663da0934d7eeb9a3684d0432adcb43986109e07bc252f |

The run manifest includes the recorded hashes of the 15 case inputs and outputs. The reviewer checked the normalized-text package hashes with the verifier and matched each recorded input/output digest pair to its metric row. Serialized trial payloads are omitted, so those hashes were not recomputed from payload bytes; this is a consistency check, not an independent replay.

SHA-256 of benchmark/sha256-manifest.json (after line-ending normalization): ecbc818bef952974038aed047b7ff04b0bc115280453b38cb1f65c1bdb50b662.

## Rerun

From `papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/` (relative to the repository root), use CPython 3.13.16 and uv 0.12.23:

    uv sync --locked --python 3.13.16
    uv run --locked python run_benchmark.py --output-dir output

The command reads only the package's fixture generator and locked environment. It writes full synthetic inputs and compressed outputs under output/trial-details.jsonl, per-trial metrics, an aggregate, and environment metadata. The generated content is synthetic and matches the public fixture generator.

The evidence files support recomputation of the reported aggregates. Because no independent replay has been recorded, the paper makes no claim that a second run reproduced the evidence output.

## Separate synthetic tooling suite

The tooling expansion is a distinct run; it is not part of the Headroom aggregation. Its evidence run was recorded as `2026-10-09T20:37:58-05:00` using CPython 3.11.9, QMD 2.8.3 (`facd35e`), ast-grep 0.45.3, and Trafilatura 2.3.0. The version, commands, per-case source-byte outcomes, marker checks, and fixture digests are in `benchmark/metrics/tooling-suite-results.json`. `benchmark/tooling-fixtures.json` is the synthetic fixture source, `benchmark/TOOLING-SUITE-METHOD.md` describes the calculations, and `benchmark/tooling-suite-sha256-manifest.json` binds normalized-text digests for the source, runner, method, result file, and verifier. Like the Headroom manifest, it does not hash itself; verify it with `python verify_sha256_manifest.py --manifest tooling-suite-sha256-manifest.json` from `benchmark/`.

From `supporting/benchmark/`, run:

    python run_synthetic_tooling.py

The runner checks QMD 2.8.3 and ast-grep 0.45.3 from their `--version` outputs, and Trafilatura 2.3.0 from package metadata before any fixture work. If a required version differs, it exits with a message naming the required and detected version. It creates a temporary working directory; runs `qmd init`, `qmd collection add fixtures --name synthetic`, and `qmd update` there; and checks with `qmd status` that the index is the temporary project's `.qmd/index.sqlite`. The temporary index is removed after the command. This is isolated from the machine's default QMD index.

The five generated HTML pages are served by an ephemeral HTTP server bound to loopback and fetched locally with `urllib.request.urlopen`; the runner confirms one successful fetch per page and shuts down the server. It sends no request to an external site. ast-grep first emits an outline, then a JSON match; the matched source text is normalized to LF before UTF-8 byte counting. The prompt-prefix fixture compares two rendered strings and performs no provider call.

This run records byte outcomes for the QMD source selection, AST selection, and HTML extraction; it does not measure token or provider savings. It was executed once. An independent replay or cross-host comparison is not claimed. The checked-in result is bound to its fixture source and generated input/output hashes; the companion SHA-256 manifest does not hash itself.
