# Blind vs. Non-Blind Adversarial Review Trial Protocol

This packet defines the controlled two-arm evaluation used to test whether stripping author rationale changes defect detection on multi-language pull requests with seeded flaws.

## Design

- **Fixtures (4):** Multi-language standalone modules (`Go`, `Python`, `JavaScript`) each containing one deterministic, test-reproducible defect alongside passing unit tests for the happy path:
  1. `trial_01_race_lease_go`: Lock-release TOCTOU race in lease acquisition (`CWE-362`).
  2. `trial_02_stale_sha_gate_py`: Ancestry-only and symbolic-ref proof bypass (`CWE-345`).
  3. `trial_03_path_boundary_js`: Sibling-prefix directory traversal escape (`CWE-22`).
  4. `trial_04_silent_error_swallow_py`: Fail-open broad exception swallow in digest verification (`CWE-636`).
- **Arm A (`non_blind`):** Reviewer receives the specification, the PR diff (code + happy-path unit test), and a plausible, confident author rationale asserting correctness and test coverage.
- **Arm B (`blind`):** Reviewer receives only the specification and the identical PR diff, with all author rationale removed.
- **Isolation Rules:**
  - Reviewer subagents execute in clean-slate context (`fork_turns: "none"` / isolated session).
  - Reviewers MUST NOT read `ground-truth-rubric.json` or `fixtures/*/test_repro*` / `repro` tests.
  - Each trial logs its results in `metrics/blind-trial-results.json` using `verdict` (`PASS` vs `BLOCK`), `seeded_defect_caught` (boolean), `finding_count`, `severity_counts` (`critical`, `high`, `medium`, `low`), and `findings` summaries.

## Reproducing the Seeded Defects Locally

Each fixture includes a deterministic reproduction test confirming the defect before review:

- `trial_01_race_lease_go`: `go test ./...` (fails `TestReproConcurrentDoubleAcquire`)
- `trial_02_stale_sha_gate_py`: `python -m unittest test_repro.py` (fails `test_repro_trailing_unverified_commit_bypasses_gate`)
- `trial_03_path_boundary_js`: `node --test exporter.test.mjs` (fails sibling-prefix directory escape test)
- `trial_04_silent_error_swallow_py`: `python -m unittest test_repro.py` (fails `test_repro_corrupt_manifest_or_missing_entry_must_fail_closed`)
