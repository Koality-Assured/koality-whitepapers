# Context efficiency in agent harnesses: measuring compression, retrieval, scoped extraction, and prompt prefixes

## Abstract

Agent harnesses can reduce model-facing context by compressing tool output, retrieving selected documents, extracting a relevant code region, distilling fetched pages, or reusing a provider-side prompt prefix. These operations change different inputs and require different quality checks. This paper presents a bounded engineering study built from public synthetic fixtures, with one previously published Headroom run retained as a single component.

In the published Headroom run, Headroom AI 0.40.0 reported a mean local token-count reduction of 86.53% across 15 deterministic tool-output fixtures, with all 25 configured marker substrings retained. In a separate synthetic tooling run on 2026-10-09, QMD placed the expected document first for 4/4 lexical queries; the selected source documents averaged 80.97% fewer UTF-8 source bytes than the five-document fixture corpus. ast-grep selected a 282-byte target function from a 758-byte synthetic file and retained 3/3 markers. A local-only fetch and Trafilatura extraction reduced five synthetic HTML inputs by a mean 85.86% of UTF-8 bytes, retaining 15/15 configured marker and fact strings. A static prompt audit found exactly 216 shared prefix bytes across two synthetic prompts, with variation immediately afterward.

These are separate synthetic tasks with different units, denominators, and oracles. They cannot be added into an end-to-end savings figure. Byte reductions are not token or cost savings. The prompt-prefix result is not evidence of provider cache eligibility or a cache hit. None of these fixtures establishes semantic quality, task success, security, generalization to real workloads, or provider billing effects.

## 1. Thesis, question, audience, and structure

**Thesis.** Context-efficiency claims are useful only when each transformation is measured with a method-specific outcome and an explicit preservation check. Local reductions alone do not show that an agent completes work equally well or costs less end to end.

**Research question.** What do small, deterministic synthetic runs establish about local output compression, lexical retrieval, structural extraction, local HTML distillation, and stable prompt-prefix layout—and which outcomes remain unmeasured?

**Audience.** Engineers designing agent harnesses, infrastructure teams choosing context-management methods, and reviewers assessing small systems benchmarks.

The paper first defines the measurement boundary, then reports the Headroom run and the four-task tooling suite separately. It closes with source-backed provider-cache facts, an evidence map, limitations, and reproducibility instructions.

## 2. Methods and measurement boundary

Context management includes several operations that are not interchangeable.

| Method | What changes | Suitable local evidence | What local evidence does not establish |
| --- | --- | --- | --- |
| Tool-output compression | Text returned by a tool before it enters model context | Before/after token counts, tokenizer, preservation checks, and failure behavior | Semantic quality, task completion, or provider billing |
| Retrieval | Which stored documents are selected for a query | Ranking against known relevant documents, selected content size, and an answer-quality check | Quality on a different corpus or the full model-facing prompt size |
| Structural extraction | Which syntax subtree or symbol is retained | Correct selected node, exact required facts, and source-size comparison | Program behavior, compilation, or semantic equivalence |
| HTML fetching and distillation | A page response and its extracted text | Fetch status, byte counts, extraction quality markers, and failure behavior | Factuality or safety on arbitrary pages |
| Provider prompt caching | Whether a provider reuses a qualifying rendered prefix | Provider usage fields, request/model details, and cache-write/read or cost measurements | Cache hits from string layout alone |

The Headroom token percentages below are local tokenizer measures from the original published run. The additional tooling suite uses UTF-8 **bytes** for source and HTML comparisons. The prefix audit counts UTF-8 bytes. These dimensions are not directly comparable. No measurements from the independent tasks are combined.

All new fixtures are fictional, deterministic, and defined in the public package. The tooling suite made no remote network requests. It uses a temporary QMD project index and a temporary HTTP server bound only to loopback. Its detailed outputs and generated fixture checksums are in [`supporting/benchmark/metrics/tooling-suite-results.json`](supporting/benchmark/metrics/tooling-suite-results.json); the method is documented in [`supporting/benchmark/TOOLING-SUITE-METHOD.md`](supporting/benchmark/TOOLING-SUITE-METHOD.md).

## 3. Component A: Headroom tool-output compression

The first component is the earlier published Headroom benchmark, not a rerun of the broader tooling suite. Headroom AI 0.40.0 reported a mean token-count reduction of 86.53% across 15 deterministic synthetic fixtures: five JSON tool outputs, five build logs, and five grep-hit outputs. Category means were 64.91%, 97.52%, and 97.16%. The exact-substring oracle found all 25 configured markers after compression.

The runner used CPython 3.13.16, uv 0.12.23, Headroom AI 0.40.0, and tiktoken 0.14.0. The local `gpt-4o` tokenizer selector maps to `o200k_base`; it did not make a provider request. Headroom's reported compression ratio is its local `tokens_saved / tokens_before` measure. A second local count used compact serialized messages. Neither count is provider billing telemetry.

The fixtures deliberately repeat synthetic padding and structure. They are not sampled from real workloads. The marker oracle checks exact predetermined substrings only. The evidence run completed once; the package includes a reproduction command, but no independent replay is claimed. See the original [benchmark method](supporting/benchmark/METHOD.md), [trial metrics](supporting/benchmark/metrics/trial-metrics.json), and [summary](supporting/benchmark/metrics/summary.json).

The 86.53% value refers only to this previously published Headroom package and its 15-fixture run. No separate combined-suite Headroom statistic is reported here.

## 4. Component B: QMD synthetic lexical retrieval

The tooling suite generated five fictional Markdown documents totaling 746 UTF-8 source bytes and ran four lexical queries with QMD 2.8.3. The QMD collection was created inside a temporary project-local `.qmd` index, updated, and searched with `--no-rerank`, so these results cover BM25 lexical search rather than vector search or model reranking.

The expected document ranked first for all four queries. Each expected marker appeared in the selected source and in the returned top-hit snippet. The first-ranked source documents ranged from 129 to 165 bytes. Their unweighted mean source-byte exclusion relative to all five fixture documents was 80.97% (range 77.88–82.71%).

The size comparison is a source-corpus proxy: it compares each selected document's bytes with all five source documents' bytes. It does not count QMD's formatted response, estimate tokens, or show the full request context the model would receive. Four lexical fixtures do not establish retrieval quality on a larger or real corpus.

## 5. Component C: ast-grep scoped extraction

The suite wrote one 758-byte synthetic Python file containing three functions. Following an outline-first workflow, it ran `ast-grep outline --json=compact`, confirmed the target symbol `policy_for_request`, then used a `function_definition` pattern to return that function. ast-grep 0.45.3 returned one match. After normalizing line endings to LF, the returned match text was 282 bytes, 62.80% fewer source bytes than the complete fixture. All three configured exact markers remained in the selected function.

This result measures one structurally selected source region. It does not assess code correctness, compilation, runtime behavior, or whether the selected region is sufficient for a model to perform a task. The fixture and exact CLI method are in the [tooling-suite package](supporting/benchmark/TOOLING-SUITE-METHOD.md).

## 6. Component D: local HTML fetch and distillation

The suite generated five fictional HTML pages with repeated navigation and boilerplate. A temporary standard-library server served them only on `127.0.0.1`; each page was fetched once through the local HTTP server and extracted with Trafilatura 2.3.0. The extractor returned plain text with comments, tables, links, and images disabled.

The raw HTML inputs ranged from 1,360 to 1,378 bytes, and extracted outputs ranged from 187 to 205 bytes. The unweighted mean reduction was 85.86% of UTF-8 bytes (range 85.12–86.25%). All 15 configured exact marker and fact strings remained in the extracted text.

This checks extraction on five generated pages only. The marker oracle does not establish factuality, protection from malicious page content, quality on arbitrary sites, or token savings. No remote website was fetched and no prompt-injection behavior was tested.

## 7. Component E: static prompt-prefix audit

The fixture contains two complete synthetic prompts that share a declared 216-byte UTF-8 prefix, followed by different request text. The static audit found a 216-byte longest common prefix, so the first differing byte was directly after that shared prefix. This is one pairwise string comparison over two prompt fixtures.

The run made no provider request and did not tokenize the prompts. It establishes only the local byte-level layout of these two strings. It does not establish that a provider accepts the prompt shape, that the prefix meets provider or model eligibility conditions, or that any request hits a cache.

Provider documentation describes cache conditions that vary by provider and model and exposes response usage fields for observing actual cache reads or writes. The [source log](supporting/SOURCES.md) records the official sources and access date. This paper reports no provider-cache measurement.

## 8. Cross-method interpretation

The components differ in units, work, and quality checks. Headroom reports locally counted tokens for compressed tool messages. QMD reports exact top-one document selection and selected source-document bytes. ast-grep reports one matched function's source bytes and markers. HTML extraction reports raw and extracted UTF-8 bytes and exact marker retention. The prefix audit reports shared bytes between two strings.

Each outcome is tied to its own synthetic task. No output is evidence of a combined harness run, and reductions cannot be summed or averaged into an end-to-end percentage. End-to-end claims would require paired task runs with fixed workloads, model/provider usage telemetry, quality outcomes, and cost or latency accounting under a specified deployment configuration.

## 9. Evidence map and claim status

The [claim-to-evidence ledger](supporting/CLAIM-TO-EVIDENCE.md) classifies findings as measured, primary-source fact, in-repo research, inference, or unresolved. The [source access log](supporting/SOURCES.md) gives URLs, versions or page dates, access date, what each source establishes, and its limits.

| Claim group | Evidence | Status and boundary |
| --- | --- | --- |
| Headroom 86.53%, category means, and 25/25 markers | Original benchmark manifests, runner, fixed fixtures, per-trial metrics, summary, and file hashes | Measured once on the published synthetic package; deliberately repetitive, with no independent replay |
| QMD 4/4 top-one and 4/4 hit-snippet markers | Synthetic fixture source, QMD 2.8.3 run, temporary local index, query rows, and hashes | Measured on four lexical queries only; source-byte comparison is not a token count |
| ast-grep 62.80% byte reduction and 3/3 markers | Synthetic Python source, outline result check, structured AST match, and hashes | Measured on one file and one selected function; no runtime or semantic evaluation |
| Trafilatura 85.86% byte reduction and 15/15 markers | Five local HTTP fixtures, Trafilatura extraction, per-page byte counts, and hashes | Measured on generated HTML only; no remote fetch or hostile-page evaluation |
| Prompt-prefix 216/216 bytes | Two rendered synthetic prompt inputs and longest-common-prefix calculation | Static fixture property only; provider cache result unresolved |
| Provider prompt-caching behavior | Current official OpenAI, Anthropic, and Gemini API documentation | Primary-source facts about documented conditions and telemetry; no cache result measured in this study |

## 10. Limitations

1. The fixtures are synthetic and few in number. They are not representative workload samples.
2. Results from separate tasks have different units and denominators; they cannot be added into an end-to-end efficiency number.
3. The Headroom cases intentionally repeat content, which can make the local reductions larger than for less-repetitive outputs.
4. The QMD fixture covers lexical search only, with four queries against five short documents. It does not test vectors, reranking, answer quality, or a real corpus.
5. The ast-grep result covers one Python function. Exact source markers do not establish semantic completeness or behavior.
6. The HTML result covers five generated pages and exact strings. It does not establish factuality, hostile-page safety, or broader extraction quality.
7. The prompt audit does not count model tokens or observe cache usage. Provider cache behavior depends on current provider-specific request conditions and should be evaluated through provider telemetry.
8. No model task-success rate, quality comparison, latency, production traffic, cost, provider billing, security effectiveness, or regulatory compliance is measured.
9. The Headroom package has a single evidence run. The synthetic tooling suite was run once on the recorded host and runtime; no independent replay or cross-host comparison is claimed.

## 11. Reproducibility

The original Headroom run is documented in [REPRODUCIBILITY.md](supporting/REPRODUCIBILITY.md) and can be rerun from the benchmark package with its pinned uv lock. The new tooling suite records Python, QMD, ast-grep, and Trafilatura versions and the SHA-256 of the fixture source and generated inputs/outputs. Its [package digest manifest](supporting/benchmark/tooling-suite-sha256-manifest.json) binds the fixture source, runner, method, and result file. The [benchmark package verifier](supporting/benchmark/verify_sha256_manifest.py) normalizes CRLF and CR line endings to LF before checking either package manifest, so the digests are stable on Windows checkouts. The tooling runner requires QMD 2.8.3, ast-grep 0.45.3, and Trafilatura 2.3.0 and stops before measurement if a version differs.

From `supporting/benchmark/`, run:

    python run_synthetic_tooling.py

QMD creates and uses a temporary project-local index; the runner verifies its location and removes it after the run. The synthetic HTTP server binds only to loopback and is shut down on exit. The suite makes no external network requests. Full commands and calculation rules are in [`TOOLING-SUITE-METHOD.md`](supporting/benchmark/TOOLING-SUITE-METHOD.md). Re-running may record a new timestamp or tool version; the recorded result file describes the specific evidence run above.

## 12. Conclusion

These bounded fixtures show how to measure context transformations without treating unlike outcomes as interchangeable. The published Headroom run reports local token-count compression and marker retention. The new synthetic suite separately checks lexical top-one retrieval, scoped AST selection, local HTML extraction, and static prompt layout in bytes. Each result is useful only within its stated fixture and oracle. None demonstrates end-to-end savings, task-quality preservation, or provider cache hits.

## References

- Headroom AI 0.40.0 [release](https://github.com/headroomlabs-ai/headroom/releases/tag/v0.40.0), [versioned compression source](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/headroom/compress.py), and [compression pipeline documentation](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/docs/content/docs/how-compression-works.mdx).
- tiktoken 0.14.0 [package metadata](https://pypi.org/project/tiktoken/0.14.0/), [model mapping](https://github.com/openai/tiktoken/blob/0.14.0/tiktoken/model.py), and [tokenizer API documentation](https://github.com/openai/tiktoken/blob/0.14.0/README.md).
- QMD [v2.8.3 release](https://github.com/tobi/qmd/releases/tag/v2.8.3) and [v2.8.3 search syntax](https://github.com/tobi/qmd/blob/v2.8.3/docs/SYNTAX.md).
- ast-grep [v0.45.3 release](https://github.com/ast-grep/ast-grep/releases/tag/0.45.3), [`outline` CLI reference](https://ast-grep.github.io/reference/cli/outline), and [`run` CLI reference](https://ast-grep.github.io/reference/cli/run).
- Trafilatura 2.3.0 [package page](https://pypi.org/project/trafilatura/2.3.0/) and [official extraction documentation](https://trafilatura.readthedocs.io/en/stable/quickstart.html).
- OpenAI [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), Anthropic [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), and Google Gemini API [context caching](https://ai.google.dev/gemini-api/docs/caching).

No legal, regulatory, security-effectiveness, or compliance claim is made.
