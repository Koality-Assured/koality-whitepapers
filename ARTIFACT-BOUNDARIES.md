# Public and private artifact boundary

## Approval status

The owner instructed the team to complete the independent reviewer's requested work and then publish. The parent recorded that instruction as approval of the initial 17-file public inventory below. The owner has now also explicitly approved the proposed README as item 18 and the expanded 18-file inventory. All 18 files are approved for public release.

The initial 17-file package passed independent review. The reviewer matched listed artifact hashes against package bytes and matched each recorded input/output digest pair to its metric row; the lockfile hash scope is accurate, and no private revision or host/user paths remain. Serialized trial payloads are omitted, so their hashes were not recomputed from payload bytes. This was a manifest-consistency check, not an independent replay. The reviewer also audited the README and revised 18-file inventory, confirming its constrained content, resolving all four links, and matching the inventory to the files present. The reviewer approved the expanded package once item 18 received owner approval.

## Owner-approved initial 17-file inventory

| # | File | Public content |
| ---: | --- | --- |
| 1 | PAPER.md | Bounded synthetic study of Headroom tool-output compression, results, and limitations. |
| 2 | CLAIM-TO-EVIDENCE.md | Claim classifications, evidence paths, methods, and caveats. |
| 3 | SOURCES.md | Primary-source URLs, access dates, versions or page dates, and limits. |
| 4 | REPRODUCIBILITY.md | Pinned environment, rerun command, hashes, and replay status. |
| 5 | ARTIFACT-BOUNDARIES.md | This approved public/private inventory. |
| 6 | OPEN-DECISIONS.md | Full-package review gate and current status. |
| 7 | PORTFOLIO-DESCRIPTION.md | Concise, evidence-bounded portfolio summary. |
| 8 | benchmark/METHOD.md | Public benchmark procedure, configuration, fixture limits, and source basis. |
| 9 | benchmark/fixtures.py | Deterministic synthetic tool-output fixtures only. |
| 10 | benchmark/run_benchmark.py | Local Headroom runner; no provider client or prompt input. |
| 11 | benchmark/pyproject.toml | Pinned direct environment declaration. |
| 12 | benchmark/uv.lock | Locked dependency resolution. |
| 13 | benchmark/method-manifest.json | Run method, versions, source log, measured summary, and limits. |
| 14 | benchmark/run-manifest.json | Safe runtime attestation, file hashes, and hashes for all 15 serialized input/output pairs. |
| 15 | benchmark/metrics/summary.json | Aggregate and category metrics. |
| 16 | benchmark/metrics/trial-metrics.json | Sanitized per-trial metrics and exact-marker counts. |
| 17 | benchmark/sha256-manifest.json | SHA-256 values for the benchmark source, configuration, and metrics files. |

The public fixtures use synthetic identifiers and paths such as synthetic/src/module-0/file-0000.py. Re-running the public command writes generated synthetic inputs and compressed outputs locally under the benchmark output directory.

## Approved item 18

| # | File | Public content | Status |
| ---: | --- | --- | --- |
| 18 | README.md | Index with the repository title, one bounded scope sentence, and links to the paper, claim ledger, benchmark method, and reproducibility instructions. It adds no results, examples, or raw data. | Owner-approved; independently reviewed. |

## Excluded private materials

| Material | Boundary |
| --- | --- |
| October 9 internal evaluation and any metrics or conclusions derived from it | Internal-only; none are copied into this paper package. |
| Private run's exact messages, prompts, fixture generator, or replay invocation | Excluded. |
| Raw trial logs, screenshots, traces, fallback-run artifacts, and host diagnostics | Excluded. |
| Webfetch inputs and results, including instruction-shaped message content | Excluded; no webfetch result or security claim is reported. |
| Internal ai-router source revisions, commits, repository paths, and machine-specific paths | Excluded; the public package binds itself through its own file and case hashes. |
| Credentials, personal data, production records, or user content | Excluded. |
| Historical 2026-08-31 numbers and unreviewed QMD, ast-grep, or provider-cache results | Excluded from the empirical claims. |
| Unsupported provider-billing, semantic-fidelity, task-success, security-effectiveness, or regulatory claims | Excluded from the conclusions. |

## Checks recorded

- Owner approval is recorded for all 18 files in this inventory.
- Independent reviewer returned GO for the corrected public benchmark package.
- The reviewer checked listed benchmark artifact hashes against package bytes and matched each recorded input/output digest pair to its metric row.
- Serialized trial payloads are omitted, so hashes were not recomputed from payload bytes; this was a manifest-consistency check, not an independent replay.
- The lockfile record count includes the local virtual project entry; downloadable dependency artifacts have hashes, while the local project entry does not.
- The package contains no internal repository revision, private path, host/user path, prompt text, secret, or personal data.
- The published command reads the public fixtures and lockfile only. No independent replay is claimed.
- The README and revised 18-file inventory passed focused independent review.

## Release gate

The exact 18-file boundary is owner-approved and has package-wide independent reviewer GO. Any change to these files or their claims requires another review.
