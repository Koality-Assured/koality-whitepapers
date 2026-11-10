# Diagrams: Commit-Bound Proof Gates and Blind Adversarial Review

Canonical Mermaid sources for the whitepaper and blog pair on commit-bound proof gates in `Koality-Assured/agent-factory` (PR #9 contracts) and the offline verification suite in [`proof_gate.py`](../benchmark/proof_gate.py).

## Inventory

| File | Kind | Scope |
| --- | --- | --- |
| [`01-promotion-gate-topology.mmd`](./01-promotion-gate-topology.mmd) | `flowchart TD` | Multi-stage promotion pipeline from Leo fix through Kenji proof, Nadia blind review, Simone PR guard, Julian pre-merge check, and human squash merge. |
| [`02-commit-invalidation-sequence.mmd`](./02-commit-invalidation-sequence.mmd) | `sequenceDiagram` | Post-proof invalidation across `amend`, `rebase`, `cherry-pick`, trailing commits, and dirty worktrees versus a valid re-proof loop. |
| [`03-negative-routing-boundary.mmd`](./03-negative-routing-boundary.mmd) | `flowchart LR` | `direct` vs. `full-assurance` negative-routing boundary and the documented Nadia gate conflict on `direct` runs. |

## 1. Multi-stage promotion gate topology

Source: [`01-promotion-gate-topology.mmd`](./01-promotion-gate-topology.mmd). Shows separation of `mutate` and `read-only` authority, the re-proof loop when accepted review fixes advance `HEAD`, and trailer preservation across GitHub squash merges onto `main`.

```mermaid
flowchart TD
    accTitle: Multi-stage commit-bound promotion gate topology
    accDescr: Promotion flow from isolated Leo fix through Kenji target_commit_sha proof, Nadia clean-slate blind review, Simone branch-tip PR guard with re-proof loop, Julian pre-merge exact-tip and ancestry verification, and human squash merge onto main.

    ADRIAN["Adrian (read-only): Hold run-lock, route tier"]

    subgraph S1["Stage 1: Isolated Fix and Commit-Bound Proof"]
        LEO["Leo (mutate worktree): Commit C1 with X-Factory trailers"]
        KENJI["Kenji (read-only vs prod): Replay or staging run"]
        PROOF["proof.json (status PASS, target_commit_sha = C1)"]
        LEO --> KENJI
        KENJI --> PROOF
    end

    subgraph S2["Stage 2: Blind Adversarial Review and PR Guard"]
        NADIA["Nadia (read-only, clean-slate): Blind diff review, no author rationale"]
        SIMONE["Simone (mutate review fixes): Adjudicate accepted, rejected, deferred"]
        FIX_LOOP{"Accepted fixes mutate HEAD?"}
        PR_GUARD{"Nadia cleared and target_commit_sha == branch_tip?"}
        PR_OPEN["Simone opens PR toward main (sole PR agent)"]
        PROOF --> NADIA
        NADIA --> SIMONE
        SIMONE --> FIX_LOOP
        FIX_LOOP -- "Yes (new HEAD invalidates PASS)" --> KENJI
        FIX_LOOP -- "No (HEAD unchanged)" --> PR_GUARD
        PR_GUARD -- "Yes" --> PR_OPEN
    end

    subgraph S3["Stage 3: Pre-Merge Verification and Human Merge"]
        JULIAN["Julian (read-only): Audit diff and X-Factory trailers"]
        PRE_MERGE{"HEAD == target_commit_sha, git merge-base --is-ancestor, clean worktree?"}
        HUMAN["Human Merge: Squash onto main keeping X-Factory-Run and X-Factory-Ledger-ID"]
        PR_OPEN --> JULIAN
        JULIAN --> PRE_MERGE
        PRE_MERGE -- "Pass" --> HUMAN
    end

    FAIL["Fail Closed: Block promotion until fix and re-proof"]
    ADRIAN --> LEO
    PR_GUARD -- "Missing clearance or SHA mismatch" --> FAIL
    PRE_MERGE -- "Fail" --> FAIL
```

## 2. Post-proof commit invalidation sequence

Source: [`02-commit-invalidation-sequence.mmd`](./02-commit-invalidation-sequence.mmd). Contrasts history rewrites (`--amend`, `rebase`, `cherry-pick`), unverified trailing commits (`HEAD != target_commit_sha` even when `git merge-base --is-ancestor` exits `0`), and dirty tracked worktree drift against a fresh re-proof on `C2`.

```mermaid
sequenceDiagram
    accTitle: Post-proof Git mutation invalidation and valid re-proof sequence
    accDescr: Sequence comparing strict fail-closed rejection across amend, rebase, cherry-pick, trailing unverified commits, and dirty worktree drift against a valid re-proof loop.

    actor Author as Leo or Simone
    participant Git as Git Repo Branch HEAD
    participant Kenji as Kenji Verifier
    participant Proof as proof.json Artifact
    participant Gate as Simone and Julian Gates

    Author->>Git: Commit fix C1 with X-Factory trailers
    Kenji->>Git: Run replay or staging suite on C1
    Kenji->>Proof: Emit PASS bound to target_commit_sha = C1

    alt Case 1 - History rewrite via amend, rebase, or cherry-pick
        Author->>Git: Execute git commit --amend, git rebase, or git cherry-pick
        Note over Git: Branch tip moves to C1_rewritten (C1 orphaned)
        Gate->>Git: Run git merge-base --is-ancestor C1 HEAD
        Git-->>Gate: Exit 1 (not ancestor) and HEAD != C1
        Gate-->>Author: Fail closed (reject PR and block merge)
    else Case 2 - Unverified trailing commit C2 stacked on C1
        Author->>Git: Commit unverified change C2 on top of C1
        Gate->>Git: Run git merge-base --is-ancestor C1 C2
        Git-->>Gate: Exit 0 (ancestry-only baseline false-accepts)
        Gate->>Git: Check HEAD == target_commit_sha (C2 == C1)
        Git-->>Gate: Mismatch (C2 != C1)
        Gate-->>Author: Fail closed (HEAD commit mismatch)
    else Case 3 - Dirty tracked worktree drift after C1 proof
        Author->>Git: Edit tracked files without commit (HEAD stays C1)
        Gate->>Git: Run git status --porcelain --untracked-files=no
        Git-->>Gate: Non-empty tracked modifications
        Gate-->>Author: Fail closed (dirty tracked worktree)
    else Case 4 - Valid re-proof loop for new tip C2
        Author->>Git: Commit clean fix C2 and leave worktree clean
        Kenji->>Git: Re-run replay or staging verification on C2
        Kenji->>Proof: Re-emit PASS with target_commit_sha = C2
        Note over Gate: Nadia blind adversarial review clears C2
        Gate->>Git: Check is-ancestor C2 HEAD, HEAD == C2, clean worktree
        Git-->>Gate: Exit 0, exact SHA match C2, clean worktree
        Gate-->>Author: Pass (eligible for human squash merge)
    end
```

## 3. Negative-routing decision boundary

Source: [`03-negative-routing-boundary.mmd`](./03-negative-routing-boundary.mmd). Traces `classify_execution_tier` in [`proof_gate.py`](../benchmark/proof_gate.py): documentation and semver fast-paths route to `direct`, while CamelCase/snake_case normalized security, concurrency, public-API/schema, and cross-module triggers force `full-assurance`. Highlights the documented spec conflict where `run-spec.md` omits Nadia on `direct` runs while `nadia/AGENT.md` and `review-and-pr/SKILL.md` block PRs lacking Nadia clearance.

```mermaid
flowchart LR
    accTitle: Negative-routing boundary and direct-tier Nadia tension
    accDescr: Left-to-right routing classifier separating fast-path direct changes from CamelCase and snake_case security, auth, concurrency, public-API, and cross-module triggers that force full-assurance, plus the Nadia gate conflict on direct runs.

    IN["Input: changed_files and diff_text"]
    EMPTY{"changed_files empty?"}
    DOCS{"Docs (.md, .txt, .rst) or comment typo?"}
    SEMVER{"Manifest semver bump only?"}
    NORM["Normalize identifiers: split CamelCase and snake_case"]
    SEC{"Security or auth trigger (auth, jwt, rbac, secret, verify_proof)?"}
    CONC{"Concurrency trigger (mutex, lock, lease, atomic, race)?"}
    API{"Public API or schema (endpoint, router, openapi, schema)?"}
    XMOD{"Cross-module (over 2 prod files or multiple top modules)?"}
    SCOPED{"Scoped single-module fix (0 or 1 prod file)?"}

    DIRECT["Route: direct tier (Leo, Kenji, Simone)"]
    FULL["Route: full-assurance tier (11-agent fleet)"]
    NADIA["Nadia blind security-intent gate (required)"]
    TENSION["Spec Tension: run-spec omits Nadia on direct, while nadia and review-and-pr block PRs lacking Nadia clearance"]

    IN --> EMPTY
    EMPTY -- "Yes (fail closed)" --> FULL
    EMPTY -- "No" --> DOCS
    DOCS -- "Yes" --> DIRECT
    DOCS -- "No" --> SEMVER
    SEMVER -- "Yes" --> DIRECT
    SEMVER -- "No" --> NORM
    NORM --> SEC
    SEC -- "Yes" --> FULL
    SEC -- "No" --> CONC
    CONC -- "Yes" --> FULL
    CONC -- "No" --> API
    API -- "Yes" --> FULL
    API -- "No" --> XMOD
    XMOD -- "Yes" --> FULL
    XMOD -- "No" --> SCOPED
    SCOPED -- "Yes" --> DIRECT
    SCOPED -- "No (unclassified multi-file)" --> FULL
    FULL --> NADIA
    DIRECT -. "Documented conflict" .-> TENSION
    NADIA -. "Blocks skip on direct" .-> TENSION
```

## Validation and rendering notes

- Every diagram uses Mermaid v10/v11 compatible syntax (`flowchart TD`, `sequenceDiagram`, `flowchart LR`), double-quoted labels for nodes and edges containing punctuation, `accTitle` / `accDescr` metadata, and no raw HTML `<br>` tags.
- The three `.mmd` files are standalone Mermaid sources rendered inline by GitHub Markdown, requiring no external pre-compilation or build-host tooling.
