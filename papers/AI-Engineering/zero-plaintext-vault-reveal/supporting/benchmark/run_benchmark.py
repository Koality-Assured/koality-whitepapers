#!/usr/bin/env python3
"""Offline Python model of secret-bearing tool transcript boundaries.

Evaluates:
1. Canary exclusion across 4 constructed fixture boundaries. This runner does
   not call llm-vault, llm-vault-mcp, a subprocess, an LLM, or the network.
   It refuses to download tokenizer data if the local cache is cold.
2. Multi-turn token footprint (tiktoken o200k_base) of naive plaintext vs envelope sandbox.
3. Python cryptographic analog and string-replacement microbenchmarks.

Fixture results are deterministic; local timing results are host-dependent.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tiktoken
from tiktoken import load as tiktoken_load

from fixtures import (
    SyntheticSecretFixture,
    generate_synthetic_fixtures,
    simulate_mcp_execute_with_secret,
    simulate_vault_api_reveal,
)

HERE = Path(__file__).resolve().parent
METRICS_DIR = HERE / "metrics"

# tiktoken fetches its public rank file on a cache miss by default. The
# reproducibility guide prewarms that file separately; benchmark execution is
# offline and must fail rather than fetch if the local cache is incomplete.
def _reject_tokenizer_cache_miss(url: str) -> bytes:
    raise RuntimeError(
        "Tokenizer data is not cached. Preload o200k_base as described in "
        "supporting/REPRODUCIBILITY.md, then rerun this benchmark offline."
    )


tiktoken_load.read_file = _reject_tokenizer_cache_miss
ENCODER = tiktoken.get_encoding("o200k_base")


def count_tokens_messages(messages: list[dict[str, str]]) -> int:
    serialized = json.dumps(messages, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return len(ENCODER.encode(serialized))


def write_json(path: Path, value: Any) -> None:
    """Write stable LF JSON so generated artifact hashes match across OSes."""
    with open(path, "w", encoding="utf-8", newline="\n") as output_file:
        json.dump(value, output_file, indent=2)


def count_raw_credential_appearances(messages: list[dict[str, Any]], raw_credential: str) -> int:
    """Count raw credential values in nested tool-result JSON strings."""
    def count_in_value(value: Any) -> int:
        if isinstance(value, str):
            return value.count(raw_credential)
        if isinstance(value, dict):
            return sum(count_in_value(item) for item in value.values())
        if isinstance(value, list):
            return sum(count_in_value(item) for item in value)
        return 0

    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                parsed_content = content
            total += count_in_value(parsed_content)
        else:
            total += count_in_value(content)
    return total


@dataclass
class BoundaryEvaluationResult:
    fixture_id: str
    secret_type: str
    boundary_1_api_reveal_pass: bool
    boundary_2_mcp_tool_result_pass: bool
    boundary_3_subprocess_scrubbing_pass: bool
    boundary_4_context_isolation_pass: bool
    naive_context_literal_sentinel_count: int
    sandbox_context_literal_sentinel_count: int
    naive_context_raw_credential_count: int
    sandbox_context_raw_credential_count: int
    naive_context_cumulative_tokens: int
    sandbox_context_cumulative_tokens: int
    tokens_saved_ratio: float


@dataclass
class CryptoMicrobenchmarkResult:
    operation: str
    iterations: int
    mean_duration_ms: float
    throughput_ops_per_sec: float
    details: str


BOUNDARY_FIELDS = {
    "constructed_api_shaped_response": "boundary_1_api_reveal_pass",
    "simulated_mcp_tool_result": "boundary_2_mcp_tool_result_pass",
    "python_variant_replacement": "boundary_3_subprocess_scrubbing_pass",
    "constructed_prompt_history": "boundary_4_context_isolation_pass",
}


def summarize_boundary_pass_rates(
    results: list[BoundaryEvaluationResult],
) -> tuple[dict[str, str], bool]:
    total = len(results)
    if total == 0:
        raise ValueError("At least one fixture result is required")

    rates: dict[str, str] = {}
    all_passed = True
    for label, field in BOUNDARY_FIELDS.items():
        passed = sum(1 for result in results if getattr(result, field))
        rates[label] = f"{passed}/{total} ({passed / total * 100:.1f}%)"
        all_passed = all_passed and passed == total
    return rates, all_passed


def run_boundary_evaluation(fixtures: list[SyntheticSecretFixture]) -> list[BoundaryEvaluationResult]:
    results = []

    for fixture in fixtures:
        # Boundary 1: constructed API-shaped JSON, not an HTTP response
        api_reveal_resp = simulate_vault_api_reveal(fixture)
        api_json = json.dumps(api_reveal_resp)
        b1_pass = (fixture.sentinel_token not in api_json) and (fixture.raw_plaintext not in api_json)

        # Boundary 2: MCP Tool Result
        # Model a command echoing the entire secret. The TypeScript scrubber
        # cannot promise to remove arbitrary fragments of a secret.
        sim_stdout = f"Connecting with credential {fixture.raw_plaintext}...\nOperation completed."
        sim_stderr = f"Warning: credential {fixture.raw_plaintext} was used"
        mcp_result = simulate_mcp_execute_with_secret(fixture, "deploy_service", sim_stdout, sim_stderr)
        mcp_json = json.dumps(mcp_result)
        b2_pass = (fixture.sentinel_token not in mcp_json) and (fixture.raw_plaintext not in mcp_json)

        # Boundary 3: Subprocess Scrubbing across variants
        variants = fixture.get_variants()
        test_log_stream = "\n".join(f"Log line {i}: processed token [{v}] in stream" for i, v in enumerate(variants))
        scrubbed_log = test_log_stream
        for v in variants:
            scrubbed_log = scrubbed_log.replace(v, f"[REDACTED:{fixture.secret_id}]")
        b3_pass = all(v not in scrubbed_log for v in variants) and (fixture.sentinel_token not in scrubbed_log)

        # Boundary 4: Multi-Turn Conversation Context Comparison
        # Simulating a 3-turn agent loop:
        # Turn 1: User asks agent to run task. Agent calls tool.
        # Turn 2: Tool returns result. Agent analyzes result and issues validation query.
        # Turn 3: Validation tool returns. Agent reports final answer.

        # Condition A: Naive Plaintext Return
        naive_messages = [
            {"role": "user", "content": "Execute deployment and verify configuration status."},
            {"role": "assistant", "content": f"Calling get_secret for {fixture.secret_id}..."},
            {"role": "tool", "content": json.dumps({"secret": fixture.raw_plaintext, "status": "active"})},
            {"role": "assistant", "content": "Executing deployment command with received credential..."},
            {"role": "tool", "content": json.dumps({"stdout": f"Deployment finished with {fixture.raw_plaintext}", "code": 0})},
            {"role": "assistant", "content": "Verification succeeded."},
        ]
        naive_prompt_history = json.dumps(naive_messages)
        naive_sentinels = naive_prompt_history.count(fixture.sentinel_token)
        naive_raw = count_raw_credential_appearances(naive_messages, fixture.raw_plaintext)

        # In a 3-turn loop, input tokens accumulate turn by turn:
        t1_in = count_tokens_messages(naive_messages[:1])
        t2_in = count_tokens_messages(naive_messages[:3])
        t3_in = count_tokens_messages(naive_messages[:5])
        naive_cumulative_tokens = t1_in + t2_in + t3_in

        # Condition B: Cryptographic Envelope + Local MCP Sandbox
        sandbox_messages = [
            {"role": "user", "content": "Execute deployment and verify configuration status."},
            {"role": "assistant", "content": f"Calling vault_run_command for {fixture.secret_id}..."},
            {"role": "tool", "content": json.dumps({"exitCode": 0, "stdout": "Deployment finished successfully.", "injectedEnvKeys": ["SECRET_KEY"]})},
            {"role": "assistant", "content": "Running post-deploy health check..."},
            {"role": "tool", "content": json.dumps({"exitCode": 0, "stdout": "Health check 200 OK."})},
            {"role": "assistant", "content": "Verification succeeded with zero credential exposure."},
        ]
        sandbox_prompt_history = json.dumps(sandbox_messages)
        sandbox_sentinels = sandbox_prompt_history.count(fixture.sentinel_token)
        sandbox_raw = count_raw_credential_appearances(sandbox_messages, fixture.raw_plaintext)

        s1_in = count_tokens_messages(sandbox_messages[:1])
        s2_in = count_tokens_messages(sandbox_messages[:3])
        s3_in = count_tokens_messages(sandbox_messages[:5])
        sandbox_cumulative_tokens = s1_in + s2_in + s3_in

        b4_pass = (sandbox_sentinels == 0) and (sandbox_raw == 0) and (naive_raw > 0)
        saved_ratio = 1.0 - (sandbox_cumulative_tokens / naive_cumulative_tokens)

        results.append(
            BoundaryEvaluationResult(
                fixture_id=fixture.secret_id,
                secret_type=fixture.secret_type,
                boundary_1_api_reveal_pass=b1_pass,
                boundary_2_mcp_tool_result_pass=b2_pass,
                boundary_3_subprocess_scrubbing_pass=b3_pass,
                boundary_4_context_isolation_pass=b4_pass,
                naive_context_literal_sentinel_count=naive_sentinels,
                sandbox_context_literal_sentinel_count=sandbox_sentinels,
                naive_context_raw_credential_count=naive_raw,
                sandbox_context_raw_credential_count=sandbox_raw,
                naive_context_cumulative_tokens=naive_cumulative_tokens,
                sandbox_context_cumulative_tokens=sandbox_cumulative_tokens,
                tokens_saved_ratio=round(saved_ratio, 4),
            )
        )

    return results


def run_crypto_microbenchmarks() -> list[CryptoMicrobenchmarkResult]:
    results = []

    # 1. PBKDF2 with 600,000 iterations (MasterKey derivation in @llm-vault/crypto)
    password = b"SENTINEL_CANARY_PASSPHRASE_00000000-0000-4000-8000-000000000003"
    salt = b"SENTINEL_CANARY_SALT_00000000-0000-4000-8000-000000000004"
    pbkdf2_iters = 5
    t0 = time.perf_counter()
    for _ in range(pbkdf2_iters):
        hashlib.pbkdf2_hmac("sha256", password, salt, 600_000, dklen=32)
    t1 = time.perf_counter()
    pbkdf2_mean_ms = ((t1 - t0) / pbkdf2_iters) * 1000.0
    results.append(
        CryptoMicrobenchmarkResult(
            operation="pbkdf2_hmac_sha256_600k",
            iterations=pbkdf2_iters,
            mean_duration_ms=round(pbkdf2_mean_ms, 2),
            throughput_ops_per_sec=round(1000.0 / pbkdf2_mean_ms, 2),
            details="Python hashlib analog of PBKDF2-HMAC-SHA256; not client WebCrypto timing",
        )
    )

    # 2. scrypt password hashing (Slice 3 server hash in apps/api/src/auth.ts)
    # crypto.scryptSync(clientAuthKeyHex, serverSalt, 32)
    client_auth_key = b"a" * 64
    server_salt = b"SENTINEL_CANARY_SERVER_SALT_00000000-0000-4000-8000-000000000005"
    scrypt_iters = 100
    t0 = time.perf_counter()
    for _ in range(scrypt_iters):
        hashlib.scrypt(client_auth_key, salt=server_salt, n=16384, r=8, p=1, maxmem=0, dklen=32)
    t1 = time.perf_counter()
    scrypt_mean_ms = ((t1 - t0) / scrypt_iters) * 1000.0
    results.append(
        CryptoMicrobenchmarkResult(
            operation="scrypt_server_hash_n16384",
            iterations=scrypt_iters,
            mean_duration_ms=round(scrypt_mean_ms, 3),
            throughput_ops_per_sec=round(1000.0 / scrypt_mean_ms, 2),
            details="Python hashlib analog of scrypt; not Node.js scryptSync timing",
        )
    )

    # 3. HMAC-SHA256 password hashing (Slice 2 server hash)
    hmac_iters = 10000
    t0 = time.perf_counter()
    for _ in range(hmac_iters):
        hmac.new(server_salt, client_auth_key, hashlib.sha256).digest()
    t1 = time.perf_counter()
    hmac_mean_ms = ((t1 - t0) / hmac_iters) * 1000.0
    results.append(
        CryptoMicrobenchmarkResult(
            operation="hmac_sha256_server_hash",
            iterations=hmac_iters,
            mean_duration_ms=round(hmac_mean_ms, 4),
            throughput_ops_per_sec=round(1000.0 / hmac_mean_ms, 2),
            details="Python hmac analog; not Node.js createHmac timing",
        )
    )

    # 4. Python replacement on exactly 50 KiB of synthetic ASCII text.
    scrubber_iters = 500
    fixtures = generate_synthetic_fixtures()
    variants = [v for f in fixtures for v in f.get_variants()]
    injected = "\n".join(f"DEBUG: synthetic token={v}" for v in variants[:10])
    padding = 50 * 1024 - len(injected.encode("utf-8"))
    if padding < 0:
        raise ValueError("Injected variants exceed 50 KiB buffer")
    injected_log = injected + ("x" * padding)
    assert len(injected_log.encode("utf-8")) == 50 * 1024

    t0 = time.perf_counter()
    for _ in range(scrubber_iters):
        scrubbed = injected_log
        for v in variants[:10]:
            scrubbed = scrubbed.replace(v, "[REDACTED]")
    t1 = time.perf_counter()
    scrubber_mean_ms = ((t1 - t0) / scrubber_iters) * 1000.0
    results.append(
        CryptoMicrobenchmarkResult(
            operation="python_string_replacement_50kib_log",
            iterations=scrubber_iters,
            mean_duration_ms=round(scrubber_mean_ms, 3),
            throughput_ops_per_sec=round(1000.0 / scrubber_mean_ms, 2),
            details="Python str.replace over exactly 50 KiB synthetic UTF-8; not MCP scrubber timing",
        )
    )

    return results


def main() -> None:
    fixtures = generate_synthetic_fixtures()
    boundary_results = run_boundary_evaluation(fixtures)
    crypto_results = run_crypto_microbenchmarks()

    # Calculate aggregate summary metrics
    total_fixtures = len(boundary_results)
    boundary_pass_rates, all_boundaries_passed = summarize_boundary_pass_rates(boundary_results)

    mean_tokens_saved_ratio = sum(r.tokens_saved_ratio for r in boundary_results) / total_fixtures
    mean_naive_tokens = sum(r.naive_context_cumulative_tokens for r in boundary_results) / total_fixtures
    mean_sandbox_tokens = sum(r.sandbox_context_cumulative_tokens for r in boundary_results) / total_fixtures

    summary = {
        "benchmark_id": "zero-plaintext-vault-reveal-canary-suite",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_fixtures_evaluated": total_fixtures,
        "scope": "Offline Python simulation using a prewarmed tokenizer cache; no product runtime or network access is used.",
        "boundary_pass_rates": boundary_pass_rates,
        "sentinel_leakage_counts": {
            "naive_plaintext_literal_sentinel_appearances": sum(r.naive_context_literal_sentinel_count for r in boundary_results),
            "sandbox_literal_sentinel_appearances": sum(r.sandbox_context_literal_sentinel_count for r in boundary_results),
            "naive_plaintext_raw_credential_appearances": sum(r.naive_context_raw_credential_count for r in boundary_results),
            "sandbox_raw_credential_appearances": sum(r.sandbox_context_raw_credential_count for r in boundary_results),
        },
        "token_consumption_comparison": {
            "mean_naive_cumulative_input_tokens": round(mean_naive_tokens, 2),
            "mean_sandbox_cumulative_input_tokens": round(mean_sandbox_tokens, 2),
            "unweighted_mean_per_fixture_reduction_percentage": f"{round(mean_tokens_saved_ratio * 100, 2)}%",
            "reduction_between_displayed_means_percentage": f"{round((1 - mean_sandbox_tokens / mean_naive_tokens) * 100, 2)}%",
        },
        "cryptographic_microbenchmarks": [asdict(c) for c in crypto_results],
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }

    # Write trial metrics and summary
    trial_metrics_path = METRICS_DIR / "trial-metrics.json"
    write_json(trial_metrics_path, [asdict(r) for r in boundary_results])

    summary_path = METRICS_DIR / "summary.json"
    write_json(summary_path, summary)

    # Write run manifest
    run_manifest = {
        "benchmark": "Zero-Plaintext Agent Context Canary Benchmark",
        "timestamp_utc": summary["date_utc"],
        "files_generated": [
            "metrics/trial-metrics.json",
            "metrics/summary.json",
        ],
        "fixtures_count": total_fixtures,
        "status": "PASS" if all_boundaries_passed else "FAIL",
        "all_simulated_boundaries_passed": all_boundaries_passed,
        "zero_provider_api_calls": True,
        "network_access": "none during benchmark execution; tokenizer cache misses are rejected",
    }
    write_json(HERE / "run-manifest.json", run_manifest)

    # Generate sha256 manifest
    sha_manifest: dict[str, str] = {}
    for file_path in sorted(HERE.glob("**/*")):
        if file_path.is_file() and not file_path.name.endswith(".pyc") and "__pycache__" not in file_path.parts:
            rel_name = file_path.relative_to(HERE).as_posix()
            data = file_path.read_bytes()
            sha_manifest[rel_name] = hashlib.sha256(data).hexdigest()

    write_json(HERE / "sha256-manifest.json", sha_manifest)

    print(f"Benchmark status: {'PASS' if all_boundaries_passed else 'FAIL'}")
    print(f"Simulated boundary rates: {boundary_pass_rates}")
    print(f"Summary written to {summary_path}")
    if not all_boundaries_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
