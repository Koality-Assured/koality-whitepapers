# Primary-source bibliography and access log

The versioned sources below were checked on 2026-10-09 in America/Chicago. Living provider documentation can change after access. A release page or source file establishes project-published facts about that version; it does not independently validate the benchmark output.

| ID | Official source | Version or page date | What it establishes | Limits |
| --- | --- | --- | --- | --- |
| S1 | [Headroom v0.40.0 release](https://github.com/headroomlabs-ai/headroom/releases/tag/v0.40.0) | Released 2026-10-06; accessed 2026-10-09. | Release identity and project release notes for the pinned version. | Release notes do not establish performance on these fixtures or other workloads. |
| S2 | [Headroom v0.40.0 compression source](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/headroom/compress.py) | Version tag v0.40.0; accessed 2026-10-09. | Public compress API, configuration fields, result metrics, and compression-ratio definition. | Source semantics do not validate semantic quality or the independent accuracy of the trial files. |
| S3 | [Headroom v0.40.0 compression pipeline documentation](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/docs/content/docs/how-compression-works.mdx) | Version tag v0.40.0; accessed 2026-10-09. | Describes the vendor's compression pipeline. | Vendor documentation, not an independent implementation audit or quality result. |
| S4 | [Python 3.13.16 release](https://www.python.org/downloads/release/python-31316/) | Released 2026-09-30; accessed 2026-10-09. | Official runtime release identity and date. | The benchmark manifest establishes which runtime the run recorded. |
| S5 | [uv 0.12.23 release](https://github.com/astral-sh/uv/releases/tag/0.12.23) | Released 2026-10-03; accessed 2026-10-09. | Official uv release identity and date. | The benchmark manifest establishes the version recorded for this run. |
| S6 | [tiktoken 0.14.0 package page](https://pypi.org/project/tiktoken/0.14.0/) | Released 2026-08-17; accessed 2026-10-09. | Published package metadata and release artifacts. | Package metadata does not establish provider billing behavior. |
| S7 | [tiktoken 0.14.0 model mapping](https://github.com/openai/tiktoken/blob/0.14.0/tiktoken/model.py) | Version tag 0.14.0; accessed 2026-10-09. | Maps gpt-4o to o200k_base in that tagged source. | Confirms the tokenizer mapping only, not equivalence to provider request accounting. |
| S8 | [tiktoken 0.14.0 tokenizer API documentation](https://github.com/openai/tiktoken/blob/0.14.0/README.md) | Version tag 0.14.0; accessed 2026-10-09. | Documents explicit get_encoding() use. | Does not establish how Headroom counts or how a provider bills. |
| S9 | [Trafilatura 2.3.1 package page](https://pypi.org/project/trafilatura/2.3.1/) | Released 2026-10-06; accessed 2026-10-09. | Published package identity in the reused lock environment. | Trafilatura is not imported or used for these benchmark measurements. |
| S10 | [OpenAI prompt caching documentation](https://developers.openai.com/api/docs/guides/prompt-caching) | Living documentation; accessed 2026-10-09. | Describes prefix caching conditions and cached-token usage fields; notes that a session alone does not guarantee a cache hit. | Model- and configuration-dependent; no provider call was made in this study. |
| S11 | [Anthropic prompt caching documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) | Living documentation; accessed 2026-10-09. | Describes cache-read and cache-creation usage information. | Provider-specific background; no cache outcome was measured. |
| S12 | [Gemini API context caching documentation](https://ai.google.dev/gemini-api/docs/caching) | Last updated 2026-10-09 UTC; accessed 2026-10-09. | Describes supported context-caching flows and cached-token usage reporting. | Provider- and API-flow-specific; no Gemini request was made. |

## Regulatory scope

The paper makes no legal, regulatory, or compliance claim. No regulatory source was needed or used.

## Unmeasured methods

QMD retrieval, ast-grep structural extraction, and provider prompt caching are background categories only. No result from these methods appears in the empirical findings.
