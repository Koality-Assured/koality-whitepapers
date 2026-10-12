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

#### Context Efficiency Methods

A synthetic study of Headroom tool-output compression on deliberately repetitive fixtures. It reports local token-count changes and an exact-marker check; it does not assess semantic preservation, task success, or provider billing.

- [Read the paper](papers/AI-Engineering/context-efficiency-methods/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/context-efficiency-methods/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/context-efficiency-methods/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/context-efficiency-methods/supporting/REPRODUCIBILITY.md)
- [Benchmark method](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/METHOD.md)
- [Full benchmark package](papers/AI-Engineering/context-efficiency-methods/supporting/benchmark/)

#### Clean-Slate Specialist Context

A deterministic synthetic evaluation of subagent context isolation and the multi-agent context tax. It measures local token reductions (99.72% vs. 60k inherited baseline) and distractor collision rates across 15 software tasks; it does not represent live provider billing or unmeasured model checkpoints.

- [Read the paper](papers/AI-Engineering/clean-slate-specialist-context/PAPER.md)
- [Claim-to-evidence ledger](papers/AI-Engineering/clean-slate-specialist-context/supporting/CLAIM-TO-EVIDENCE.md)
- [Primary-source access log](papers/AI-Engineering/clean-slate-specialist-context/supporting/SOURCES.md)
- [Reproducibility guide](papers/AI-Engineering/clean-slate-specialist-context/supporting/REPRODUCIBILITY.md)
- [Benchmark method](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/METHOD.md)
- [Full benchmark package](papers/AI-Engineering/clean-slate-specialist-context/supporting/benchmark/)

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
