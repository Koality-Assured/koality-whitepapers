# Synthetic Clean-Slate Specialist Context Evaluation Method

This benchmark package measures the token bloat ("context tax"), distractor collision rate, and task completion fidelity of multi-agent subagent delegation across clean-slate vs. transcript-inherited context states.

No production data, private paths, instructions, credentials, or live provider requests are used. All fixtures, code targets, and conversation logs are 100% deterministic and synthetic.

## Reproduce

Use CPython 3.13.16 and `uv 0.12.23` with the checked-in lockfile. The direct dependency is `tiktoken==0.14.0`.

```bash
uv sync --locked --python 3.13.16
uv run --locked python run_benchmark.py
uv run --locked python verify_sha256_manifest.py
```

The run writes sanitized per-trial metrics to `metrics/trial-metrics.json` and aggregate statistics to `metrics/summary.json`.

## Method and Experimental Design

### 1. Task Archetypes and Variants
The benchmark defines 15 distinct software engineering tasks across 3 archetypes (5 variants each):
- **Archetype A: Code Syntax & Logic Repair (`code_repair`)**: Adds an error guard and fallback value to an arithmetic function in `src/synthetic_service/handler_vXX.py`. Oracle requires exact marker `SYNTHETIC_MARKER_REPAIR_VXX_OK`.
- **Archetype B: RBAC Policy Audit (`rbac_audit`)**: Inspects endpoint route handlers in `src/synthetic_auth/policy_vXX.py` to identify an unadorned function and apply `@enforce_rbac(role='admin')`. Oracle requires exact marker `SYNTHETIC_MARKER_RBAC_VXX_VERIFIED`.
- **Archetype C: Structured Configuration Extraction (`schema_extraction`)**: Extracts timeout and connection settings from `config/synthetic_config/settings_vXX.json` into a standardized envelope. Oracle requires exact marker key `SYNTHETIC_MARKER_SCHEMA_VXX_EXTRACTED`.

### 2. Context Conditions
Each task is evaluated across 5 dispatch conditions:
- `clean_slate`: Subagent receives only the 4-part declarative task contract (Authority, Scope, Targets, Cost Layers). Zero parent conversation history.
- `fork_10k`: Contract prepended with ~10,000 tokens of synthetic coordinator history.
- `fork_30k`: Contract prepended with ~30,000 tokens of synthetic coordinator history.
- `fork_60k`: Contract prepended with ~60,000 tokens of synthetic coordinator history.
- `fork_90k`: Contract prepended with ~90,000 tokens of synthetic coordinator history.

### 3. Semantic Distractor Injection
In the inherited history conditions (10k–90k tokens), realistic engineering noise is injected:
- Obsolete compiler outputs and build logs.
- Historical git diff hunks.
- Stale, deprecated function signatures and config keys (e.g., `calculate_metric_deprecated_vXX`, `legacy_allow_anonymous_debug_vXX`, `deprecated_legacy_timeout_sec_vXX`).
Distractor collision occurs when a subagent references these stale identifiers rather than the active task targets, failing the deterministic oracle.

### 4. Multi-Turn Token Accounting
The benchmark simulates a 3-turn interactive tool-use loop:
- Turn 1: Subagent reads target file or AST outline.
- Turn 2: Subagent applies code patch or extracts schema.
- Turn 3: Subagent validates output and returns structured completion envelope.

Tokens are measured using `tiktoken 0.14.0` with the `o200k_base` encoding over compact JSON serialization of the complete message list at each turn. Cumulative input tokens represent the sum of input tokens processed across Turns 1, 2, and 3.

### 5. Financial Cost Modeling
Costs are modeled under standard frontier pricing:
- Uncached input: $2.50 per 1M tokens.
- Cached input (prefix match after Turn 1): $1.25 per 1M tokens (50% discount).
- Output tokens: $10.00 per 1M tokens.

## Limitations and Caveats
- **Local Tokenizer Caveat**: `tiktoken` counts local serialized messages. Provider APIs apply proprietary framing tokens, delimiter overhead, and internal tokenizer mappings that vary from raw JSON serialization.
- **Offline Simulation**: Zero live provider API calls were made. Distractor collision probabilities reflect established academic attention degradation curves (Liu et al., 2024; Chroma, 2025) rather than a single live model checkpoint.
- **Host Diagnostics**: The recorded run used Windows x86_64 and CPython 3.13.16. Execution timing is an environment diagnostic, not a benchmarked software property.
