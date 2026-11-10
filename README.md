<div align="center">
  <img src="assets/koality-whitepapers-logo.svg" width="72" height="72" alt="Original Koality-Assured white-paper mark: a layered document with a highlighted reference tab." />
  <h1>Koality-Assured Whitepapers</h1>
  <p>A domain-organized series of technical white papers, with documented sources, methods, and evidence limits.</p>
  <p>
    <sub><strong>DOMAIN-ORGANIZED</strong> &nbsp;·&nbsp; <strong>SOURCES</strong> &nbsp;·&nbsp; <strong>METHODS &amp; LIMITS</strong></sub>
  </p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
    <a href="#"><img src="https://img.shields.io/badge/domain-whitepapers-blueviolet.svg" alt="Domain: Whitepapers" /></a>
    <a href="https://conventionalcommits.org"><img src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg" alt="Conventional Commits" /></a>
  </p>
  <img src="assets/koality-whitepapers-banner.svg" width="100%" alt="Abstract publication cover illustration with layered paper, reference lines, and an evidence marker." />
</div>

## Catalog

### AI Engineering

#### Clean-Slate Specialist Context: Quantifying the Multi-Agent Context Tax and Distractor Interference

A deterministic synthetic evaluation of subagent context isolation and the multi-agent context tax. It measures local token reductions (99.72% vs. 60k inherited baseline) and distractor collision rates across 15 software tasks; it does not represent live provider billing or unmeasured model checkpoints.

- [Read the paper](papers/AI-Engineering/clean-slate-specialist-context/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/clean-slate-specialist-context/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/clean-slate-specialist-context/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/clean-slate-specialist-context/supporting/REPRODUCIBILITY.md)
- [Benchmark method](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/METHOD.md)
- [Full benchmark package](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/)

#### Context Efficiency in Agent Harnesses: Measuring Compression, Retrieval, Scoped Extraction, and Prompt Prefixes

A synthetic study of Headroom tool-output compression on deliberately repetitive fixtures. It reports local token-count changes and an exact-marker check; it does not assess semantic preservation, task success, or provider billing.

- [Read the paper](papers/AI-Engineering/context-efficiency-methods/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/context-efficiency-methods/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/context-efficiency-methods/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/context-efficiency-methods/supporting/REPRODUCIBILITY.md)
- [Benchmark method](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/METHOD.md)
- [Full benchmark package](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/)

#### Encrypted Reveal Envelopes and Local Secret Use in Agent Tool Harnesses

Formal engineering analysis of secret handling in autonomous coding agents. Evaluates local WebCrypto envelope decryption, ephemeral memory leases with automated zeroization, and surrogate handle substitution to eliminate plaintext credential exposure in model transcripts.

- [Read the paper](papers/AI-Engineering/zero-plaintext-vault-reveal/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/REPRODUCIBILITY.md)
- [Benchmark package](papers/AI-Engineering/zero-plaintext-vault-reveal/supporting/benchmark/)

#### Precision-First Context Scrubbing: Measuring Synthetic Format-Marker Detection and Finding-Output Size

Empirical benchmarking of context scrubber sensitivity and token expansion across synthetic test fixtures. Establishes mathematical precision boundaries (>=0.95 gate) to prevent false-positive cascades from bloating agent context windows.

- [Read the paper](papers/AI-Engineering/precision-first-context-scrubbing/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/precision-first-context-scrubbing/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/precision-first-context-scrubbing/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/precision-first-context-scrubbing/supporting/REPRODUCIBILITY.md)
- [Benchmark package](papers/AI-Engineering/precision-first-context-scrubbing/supporting/benchmark/)

#### Empirical Retrieval Cost Layers in Autonomous Agent Systems: Benchmarking BM25, Dense Semantic Vectors, and AST-Grep Against Context Tax in Developer Workflows

Comparative empirical benchmark evaluating lexical BM25 (qmd), dense semantic vector retrieval, ast-grep structural slicing, and Headroom tool compression against brute-force recursive grep across multi-turn developer sessions. Demonstrates up to 93% token reduction while preserving exact fact recall.

- [Read the paper](papers/AI-Engineering/empirical-retrieval-cost-layers/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/empirical-retrieval-cost-layers/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/empirical-retrieval-cost-layers/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/empirical-retrieval-cost-layers/supporting/REPRODUCIBILITY.md)
- [Benchmark package](papers/AI-Engineering/empirical-retrieval-cost-layers/supporting/benchmark/)

#### Commit-Bound Proof Gates and Blind Adversarial Review in Autonomous QA Fleets

Evaluates commit-bound proof verification (`HEAD == target_commit_sha`, Git ancestry, clean tracked worktrees, and independent reviewer attestation), negative-routing tier classification, and paired blind versus author-primed review trials across multi-language synthetic fixtures and public repository promotion contracts.

- [Read the paper](papers/AI-Engineering/commit-bound-proof-gates/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/commit-bound-proof-gates/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/commit-bound-proof-gates/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/commit-bound-proof-gates/supporting/REPRODUCIBILITY.md)
- [Benchmark package](papers/AI-Engineering/commit-bound-proof-gates/supporting/benchmark/)

## Paper format

Each catalog entry points to a standalone paper at `PAPER.md`. Evidence ledgers, source logs, and reproduction files live in its `supporting/` directory.

For future papers, use this minimal folder convention:

```text
papers/
  <area>/
    <paper-slug>/
      PAPER.md
      supporting/
```
