# Synthetic tooling suite: method and evidence

This suite is a small deterministic engineering check for retrieval, scoped extraction, local HTML distillation, and prompt-prefix stability. Every fixture is fictional and generated from [`tooling-fixtures.json`](tooling-fixtures.json). The raw run is [`metrics/tooling-suite-results.json`](metrics/tooling-suite-results.json).

## Run identity and environment

- Evidence run: 2026-10-09, local time (recorded as `2026-10-09T20:37:58-05:00` in the result file).
- Runtime: CPython 3.11.9; QMD 2.8.3 (`facd35e`); ast-grep 0.45.3; Trafilatura 2.3.0.
- Before creating fixtures or running a query, the script requires QMD 2.8.3, ast-grep 0.45.3, and Trafilatura 2.3.0. It parses each CLI version from `--version` and checks installed Trafilatura package metadata. A mismatch exits with an error naming the required and detected versions; QMD commit suffixes are recorded, while the version check requires 2.8.3.
- Fixture source SHA-256: `ddc021d1680621e4f2ff7bafb85f975b2557342313b9d93036d14054841c0ce6`, computed after normalizing CRLF and CR line endings to LF. Generated fixture and extraction input/output hashes cover their exact UTF-8 bytes.
- The output JSON records SHA-256 for each generated Markdown, Python, HTML, and prompt input; the AST and HTML output digests are also included.
- The package-level digests use the same CRLF/CR-to-LF normalization and are listed in [`tooling-suite-sha256-manifest.json`](tooling-suite-sha256-manifest.json). Run `python verify_sha256_manifest.py --manifest tooling-suite-sha256-manifest.json` to verify these files; the manifest does not hash itself.
- No request leaves the local machine. The web fixtures are served from an ephemeral loopback-only HTTP server. QMD uses a temporary project-local `.qmd/index.sqlite`; the runner checks that index path with `qmd status`, then removes the temporary directory on exit. It does not use or modify the user's default QMD index.

Run from this directory with CPython 3.11 and the exact QMD, ast-grep, and Trafilatura versions above installed:

    python run_synthetic_tooling.py

The script creates fixtures in a temporary directory and writes only the sanitized measurements and fixture digests to `metrics/tooling-suite-results.json`.
The runner checks versions before it creates the temporary project or performs measurements, and it fails closed if any required tool version differs.

## QMD lexical retrieval

The runner generates five short Markdown documents totalling 746 UTF-8 source bytes. It adds them to the isolated local QMD project with `qmd collection add fixtures --name synthetic`, updates the collection, and runs four BM25 searches with:

    qmd search <query> --no-rerank --format json -c synthetic -n 5

Each expected document was the top-ranked hit (4/4). Each expected marker appeared in both the selected source and the top-hit snippet (4/4). For each query, the selected source document was 129–165 bytes compared with all five source documents at 746 bytes; the unweighted mean of the four source-byte exclusion percentages was 80.9652% (range 77.8820–82.7078%).

The byte comparison describes fixture source selection only. It does not count QMD's formatted search response, estimate model tokens, evaluate a generated answer, or measure retrieval on a larger or real corpus. Vector retrieval and reranking were disabled.

## ast-grep scoped extraction

The runner writes one 758-byte fictional Python file containing three functions. It runs `ast-grep outline --json=compact` first, confirms that the outline names `policy_for_request`, then selects one `function_definition` with this pattern:

    ast-grep run --json=compact --pattern 'def policy_for_request($$$): $$$' --selector function_definition --lang python <synthetic_policy.py>

It counts the returned JSON `text` field after normalizing CRLF to LF. The target text was 282 bytes, or 62.7968% fewer source bytes than the whole fixture. All three configured exact markers remained in that selected text. This is one AST match and marker check, not a semantic, compilation, or runtime evaluation.

## Local HTML fetch and distillation

The runner generates five fictional article pages with 12 repeated synthetic boilerplate paragraphs per page. A temporary standard-library HTTP server binds only to `127.0.0.1`; the runner fetches each fixture once with `urllib.request.urlopen`, then passes the returned HTML to Trafilatura 2.3.0 `extract()` using plain-text output and comments, tables, links, and images disabled.

The five raw pages were 1,360–1,378 bytes; extracted text was 187–205 bytes. The unweighted mean reduction was 85.8605% of UTF-8 bytes (range 85.1234–86.2500%). All 15 exact configured marker/fact strings were retained. The result concerns these authored pages and this parser configuration. It does not establish factuality, resistance to hostile pages, quality on arbitrary sites, or token savings.

## Static prompt-prefix audit

Two complete synthetic prompt strings share a declared 216-byte UTF-8 prefix. The runner computes their longest common prefix and checks that the first differing byte is immediately after the declared prefix. The result is 216 shared bytes across two prompt fixtures and one pairwise comparison.

No provider request, tokenizer count, cache eligibility check, cache hit, billing result, or latency measure was made. Current provider documentation makes caching dependent on provider-specific request/model conditions and recommends response usage fields for observing actual reuse. Therefore, this fixture establishes only local string-prefix equality.

## Aggregation boundary

Headroom token-count results, QMD source bytes, AST source bytes, HTML bytes, and prompt-prefix bytes use different denominators and quality checks. They are separate synthetic tasks and are not additive. The suite reports no combined or end-to-end savings estimate.
