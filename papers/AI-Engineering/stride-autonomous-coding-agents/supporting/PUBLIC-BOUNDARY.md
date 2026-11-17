# Public boundary record

- **Package:** STRIDE threat modeling for autonomous coding agents
- **Publication date:** 2026-11-17
- **Author:** Koality-Assured
- **Decision:** Approved for public publication by the package owner.

This record defines what is public in the paper, companion post, portfolio routes, and supporting evidence files. It excludes internal workstation paths, private repository mechanics, personal handles, live credentials, and raw internal transcripts.

## Generalization decisions

| Internal category | Public treatment |
| :--- | :--- |
| Workstation paths, checkout directories, detached indexes, and scratch locations | Replaced with generalized terms such as “isolated task worktree,” “detached main-branch snapshot,” and “untrusted intake.” |
| Internal script and module names | Replaced with functional descriptions: worktree isolation manager, pre-ingestion web distillation filter, loopback-pinned output compression proxy, and public-boundary redaction gate. |
| Internal governance and routing documents | Replaced with generic references to session security contracts, inter-agent delegation protocols, and skill-dispatch catalogs. |
| Branch and worktree implementation identifiers | Generalized to unique ephemeral task branches using the documented slug/timestamp/identifier pattern. |
| Author and attribution | Published as **Koality-Assured** only. |
| Host context | Limited to the disclosed single Windows x86_64 execution host; no personal identity or workstation identifier is published. |

## Public artifact table

| Artifact | Public status | Boundary and sanitization |
| :--- | :--- | :--- |
| White paper and blog post | Public | Generalized Autonomous Developer Harness terminology; metrics, framework identifiers, and limits preserved exactly. |
| Mermaid DFD and trust-boundary diagrams | Public | Nodes use generalized roles: Human Operator, Orchestrator, Clean-Slate Subagent, Shell/MCP Tools, Retrieval Index, Untrusted Intake, and Git Remote. |
| Synthetic HTML fixtures | Public | Uses harmless markers such as `GOLD_FACT_1`, `OUTER_INJECTION_LEAK`, `Ig\u200bnore`, and the RFC 2606 `.example` domain. |
| Synthetic SSRF and truncation probes | Public | Uses `169.254.169.254:8787` and a synthetic 151-line log; no live cloud request is made. |
| Synthetic redaction fixture | Public | Uses clearly synthetic `sk-EXAMPLE_` values and a synthetic internal test address; no live credential or personal data is included. |
| Claim ledger, source log, reproducibility, and boundary record | Public supporting evidence | Paths and raw validation transcripts are omitted; authoritative public URLs and bounded evidence statements are retained. |

## Boundary verification

- The publication drafts contain no Windows or Unix workstation directory prefixes.
- The publication drafts contain no internal repository paths, credential prefixes, or real personal handles.
- The published examples are synthetic and are not presented as live exploit evidence.
- The three sanitizer bypasses remain explicitly labeled as measured limits, not remediated behavior.
- Unresolved live model compliance and the pending parser remediation remain disclosed in the paper and post.

