# Tool-output compression in agent harnesses: a bounded synthetic evaluation

## Draft status

The owner approved the exact 18-file inventory in ARTIFACT-BOUNDARIES.md, and the package-wide independent review returned GO. The benchmark ran once, and no independent replay is claimed.

## Abstract

Context-management methods change what an agent model receives, but their outcomes need separate measures. This paper evaluates one local method: Headroom compression of synthetic tool outputs.

In one pinned run, Headroom 0.40.0 reported a mean token-count reduction of 86.53% across 15 deterministic fixtures: 64.91% for JSON tool output, 97.52% for build logs, and 97.16% for grep hits. All 25 predetermined marker strings remained present under an exact-substring check. These are local counts on fixtures deliberately built with repeated synthetic padding. They do not establish semantic preservation, task success, security, provider billing, or results on less-repetitive or real workloads.

The public package contains the fixture generator, runner, lockfile, per-trial measures, summary, and file hashes. The evidence run completed once. The reproduction command is included, but no independent replay is claimed in this paper.

## 1. Scope and question

This paper is for engineers choosing context-management methods for agent harnesses and reviewers interpreting small engineering benchmarks.

The research question is: on a defined synthetic tool-output workload, how much does pinned Headroom compression change local tokenizer counts, and what does an exact-marker check establish about the transformed output?

A token-reduction percentage is hard to interpret on its own. Readers need to know how tokens were counted, what workload was used, what information was checked, how failures were handled, and whether the run can be repeated. This paper measures only local compression of tool output. Retrieval, structural extraction, and provider prompt caching appear as background categories, not evaluated alternatives.

## 2. Context-management methods

Context management includes operations with different mechanisms and outcome measures. The categories below provide background; this paper measures only tool-output compression.

| Method | Operation | Evidence needed to evaluate it |
| --- | --- | --- |
| Local compression | Transform supplied text or tool output before model use. | Before-and-after counts, tokenizer or estimator, preservation checks, and failure behavior. |
| Retrieval | Select stored material for a query. | Retrieval quality against a defined relevance or answer measure, plus context size. |
| Structural extraction | Retain selected syntax or document structure. | Extraction correctness and a task-relevant quality measure. |
| Provider prompt caching | Reuse a provider-side prefix or context representation where supported. | Provider usage fields, cache protocol, and separate billing or latency measures. |

This taxonomy separates measurement questions; it does not rank these methods. A local tokenizer count does not substitute for provider usage telemetry. An exact-marker check is narrower than a semantic or task-level test.

## 3. Methods

### 3.1 Environment and configuration

The benchmark uses CPython 3.13.16, uv 0.12.23, Headroom AI 0.40.0, and tiktoken 0.14.0. The checked-in lock resolves 108 package records. Trafilatura 2.3.1 is pinned in the reused environment but is not imported by the runner.

The runner calls Headroom's local headroom.compress() API with the gpt-4o model label, protect_recent=0, compress_user_messages=false, and kompress_model=disabled. The Kompress model weights are disabled; structural compression remains active. In tiktoken 0.14.0, gpt-4o maps to o200k_base; the label selects local token counting and does not cause a provider request. No provider API was called. Headroom's versioned source defines compression_ratio as tokens_saved / tokens_before.

The runner also counts compact JSON serialization of the complete message list with tiktoken's explicit o200k_base encoding. This is a second local count. Neither measure includes provider message framing or establishes billed tokens.

### 3.2 Fixtures and oracle

The package defines five fixed variants in each of three synthetic families: JSON tool output, build logs, and grep-hit output. Each case is a single tool message. Fixtures use deterministic arithmetic and string templates, not a random-number generator. They contain repeated padding and repeated structure intended to exercise compression, so savings may be higher than on less-repetitive inputs. They are not sampled from production traffic.

The oracle counts exact predetermined marker substrings in compact JSON-serialized messages before and after compression. There are two markers per JSON and grep case and one per build-log case, for 25 markers total. The oracle does not assess meaning, unmarked facts, task success, security, or usefulness to a model.

### 3.3 Aggregation and reporting

The primary percentages are Headroom's reported compression ratios multiplied by 100. Category means are arithmetic means of five trials. The overall mean is the unweighted arithmetic mean of the 15 trial ratios. Min–max ranges describe these observed trials; they are not confidence intervals. The independent tiktoken column reports each category's mean change in serialized-message token count.

The evidence run was performed once on Windows x86_64. Headroom reported selecting a pure-Python content-detection backend because its native Magika/ONNX detector is unsafe by default on Windows. The run completed with 15/15 nonzero Headroom token counts and no timeout. This is an observed host/runtime selection, not evidence of a software defect. Results from a host selecting another detector backend were not measured.

## 4. Results

| Fixture family | Trials | Headroom mean reduction (range) | tiktoken serialized mean reduction | Exact markers retained |
| --- | ---: | ---: | ---: | ---: |
| JSON tool output | 5 | 64.9091% (64.7873–65.0045%) | 65.2430% | 10/10 |
| Build logs | 5 | 97.5222% (97.0740–97.9049%) | 97.4879% | 5/5 |
| Grep-hit output | 5 | 97.1585% (96.5402–97.6728%) | 97.1377% | 10/10 |
| All trial rows | 15 | 86.5300% (64.7873–97.9049%) | — | 25/25 |

All trial rows had status ok; all 15 had nonzero Headroom token counts. The category and overall values can be recomputed from the public [summary](benchmark/metrics/summary.json) and [trial metrics](benchmark/metrics/trial-metrics.json). The exact fixture generator and runner are in [benchmark](benchmark/).

The marker result means only that each configured substring remained present in the serialized output. It does not show that other facts or structure survived. A high reduction on deliberately repetitive synthetic inputs is not evidence of comparable savings on real tool outputs.

## 5. Interpretation

In this fixture set, Headroom reported substantial reductions across the three categories, and the independent tiktoken count was close to the Headroom aggregate within each category. Both are local serialized-token measures. Neither is a provider billing measurement.

The check did not measure whether the compressed outputs still support a correct answer or preserve all task-relevant information. It also did not test prompt-injection handling, security, retrieval quality, structural extraction, provider caching, latency, or end-to-end task success. The fixtures were designed to contain repeated text, which limits how far the reduction percentages can be generalized.

The Windows detector selection is recorded to make the execution context clear. There was no timeout in this run. The available evidence does not compare output across detector backends or establish a defect.

## 6. Provider caching is a separate measurement

Provider caching and local compression answer different questions. OpenAI's current documentation describes reuse of matching rendered prefixes and usage fields for cached tokens and writes, while noting that a session alone does not guarantee a hit. Anthropic documents cache-read and cache-creation usage fields. Google's Gemini API documents context caching and cached-token usage reporting. These product facts are summarized with access dates and limits in [SOURCES.md](SOURCES.md).

No provider request was made in this benchmark. It therefore provides no evidence about provider cache hits, latency, input billing, or cost savings. Those outcomes require provider-specific measurements.

## 7. Limitations

1. The inputs are synthetic and intentionally repetitive; they are not representative samples of real traffic.
2. Each category has five fixed variants from one deterministic generator. The range is descriptive, not a population estimate.
3. The oracle checks only exact marker substrings. It does not assess semantic preservation, unmarked facts, or task success.
4. The benchmark evaluates Headroom 0.40.0 with one configuration and environment. It does not compare context-management methods.
5. No model-provider request, response telemetry, billing data, cache measurement, latency measure, or end-to-end task result is included.
6. The run completed once. The public package provides a rerun command, but this paper does not claim an independent replay.
7. A host that selects another content-detection backend may produce different metrics; cross-host behavior was not measured.
8. No claim is made about security effectiveness or regulatory compliance.

## 8. Reproducibility and evidence

The [reproducibility manifest](REPRODUCIBILITY.md) records the pinned versions, public command, evidence-run date, and hashes. The benchmark's [run manifest](benchmark/run-manifest.json) binds the run to the package files and hashes each of the 15 case inputs and outputs. The [SHA-256 manifest](benchmark/sha256-manifest.json) covers the method, fixture generator, runner, environment files, run manifest, and sanitized metrics. That SHA-256 manifest does not hash itself.

Run the benchmark from the benchmark directory with:

    uv sync --locked --python 3.13.16
    uv run --locked python run_benchmark.py --output-dir output

This writes local run artifacts, including full synthetic fixture inputs and compressed outputs. Those generated inputs are synthetic and match the published fixture code. The [claim-to-evidence ledger](CLAIM-TO-EVIDENCE.md) classifies measurements, primary-source facts, inferences, in-repo findings, and unresolved questions.

## 9. Conclusion

Across 15 fixed synthetic tool-output fixtures, Headroom 0.40.0 reported an unweighted mean reduction of 86.53%; the category means ranged from 64.91% to 97.52%. The exact-substring oracle found all 25 configured markers after compression. The fixture generator deliberately repeats text, and the oracle tests marker presence only. These results support a narrow statement about one local run, not semantic quality, real-workload savings, provider behavior, or general performance.

## References

- Headroom AI 0.40.0 [release](https://github.com/headroomlabs-ai/headroom/releases/tag/v0.40.0), [versioned compression source](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/headroom/compress.py), and [compression pipeline documentation](https://github.com/headroomlabs-ai/headroom/blob/v0.40.0/docs/content/docs/how-compression-works.mdx).
- tiktoken 0.14.0 [package metadata](https://pypi.org/project/tiktoken/0.14.0/), [model mapping](https://github.com/openai/tiktoken/blob/0.14.0/tiktoken/model.py), and [tokenizer API documentation](https://github.com/openai/tiktoken/blob/0.14.0/README.md).
- OpenAI [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), Anthropic [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), and Google [Gemini API context caching](https://ai.google.dev/gemini-api/docs/caching).

No legal or regulatory claim is made.
