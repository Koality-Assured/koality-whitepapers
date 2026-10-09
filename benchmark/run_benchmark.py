"""Run the public synthetic Headroom tool-output reproduction."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tiktoken
from headroom import compress

from fixtures import Fixture, build_fixtures


HEADROOM_MODEL_LABEL = "gpt-4o"
TOKENIZER_NAME = "o200k_base"
EXPECTED_PYTHON = (3, 13, 16)
EXPECTED_DISTRIBUTIONS = {
    "headroom-ai": "0.40.0",
    "tiktoken": "0.14.0",
    "trafilatura": "2.3.1",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def _versions() -> dict[str, str]:
    versions = {name: importlib.metadata.version(name) for name in EXPECTED_DISTRIBUTIONS}
    mismatches = {
        name: {"expected": expected, "actual": versions[name]}
        for name, expected in EXPECTED_DISTRIBUTIONS.items()
        if versions[name] != expected
    }
    if sys.version_info[:3] != EXPECTED_PYTHON or mismatches:
        raise RuntimeError(
            "Locked evaluation environment mismatch: "
            + json.dumps(
                {
                    "expected_python": ".".join(map(str, EXPECTED_PYTHON)),
                    "actual_python": platform.python_version(),
                    "distribution_mismatches": mismatches,
                },
                sort_keys=True,
            )
        )
    return versions


def _uv_version() -> str | None:
    try:
        completed = subprocess.run(
            ["uv", "--version"], check=True, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip()


def _marker_oracle(serialized_messages: str, markers: tuple[str, ...]) -> dict[str, Any]:
    found = [marker for marker in markers if marker in serialized_messages]
    missing = [marker for marker in markers if marker not in serialized_messages]
    return {
        "gold_marker_count": len(markers),
        "found_count": len(found),
        "missing_count": len(missing),
        "all_found": not missing,
    }


def _run_trial(fixture: Fixture, encoding: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    input_serialized = _canonical_json(fixture.messages)
    oracle_before = _marker_oracle(input_serialized, fixture.gold_markers)
    if not oracle_before["all_found"]:
        raise RuntimeError(f"Synthetic gold marker missing before compression: {fixture.fixture_id}")

    # This is Headroom's public local compress() API. The model string selects
    # Headroom's token-counting path; this runner makes no provider request.
    result = compress(
        fixture.messages,
        model=HEADROOM_MODEL_LABEL,
        protect_recent=0,
        compress_user_messages=False,
        kompress_model="disabled",
    )
    output_serialized = _canonical_json(result.messages)
    oracle_after = _marker_oracle(output_serialized, fixture.gold_markers)

    input_tiktoken = len(encoding.encode(input_serialized))
    output_tiktoken = len(encoding.encode(output_serialized))
    tiktoken_saved = input_tiktoken - output_tiktoken
    tiktoken_saved_pct = (100.0 * tiktoken_saved / input_tiktoken) if input_tiktoken else None
    metric_status = "ok" if result.tokens_before > 0 else "headroom_token_count_unavailable"

    metrics = {
        "fixture_id": fixture.fixture_id,
        "category": fixture.category,
        "variant": fixture.variant,
        "input_chars": len(input_serialized),
        "output_chars": len(output_serialized),
        "headroom_tokens_before": result.tokens_before,
        "headroom_tokens_after": result.tokens_after,
        "headroom_tokens_saved": result.tokens_saved,
        "headroom_compression_ratio": result.compression_ratio,
        "tiktoken_encoding": TOKENIZER_NAME,
        "tiktoken_serialized_tokens_before": input_tiktoken,
        "tiktoken_serialized_tokens_after": output_tiktoken,
        "tiktoken_serialized_tokens_saved": tiktoken_saved,
        "tiktoken_serialized_savings_pct": round(tiktoken_saved_pct, 4) if tiktoken_saved_pct is not None else None,
        "gold_marker_count": oracle_before["gold_marker_count"],
        "gold_markers_found_before": oracle_before["found_count"],
        "gold_markers_found_after": oracle_after["found_count"],
        "all_gold_markers_survived": oracle_after["all_found"],
        "transforms_applied": list(result.transforms_applied or []),
        "headroom_lossless_flag": result.lossless,
        "metric_status": metric_status,
        "input_messages_sha256": _sha256_text(input_serialized),
        "output_messages_sha256": _sha256_text(output_serialized),
    }
    full = {
        "fixture_id": fixture.fixture_id,
        "category": fixture.category,
        "variant": fixture.variant,
        "gold_markers": list(fixture.gold_markers),
        "input_messages": fixture.messages,
        "output_messages": result.messages,
        "metrics": metrics,
    }
    return metrics, full


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    categories = sorted({row["category"] for row in rows})
    by_category: dict[str, Any] = {}
    for category in categories:
        items = [row for row in rows if row["category"] == category]
        ratios = [100.0 * row["headroom_compression_ratio"] for row in items]
        saved_tokens = [float(row["headroom_tokens_saved"]) for row in items]
        tiktoken_savings = [float(row["tiktoken_serialized_savings_pct"]) for row in items]
        marker_count = sum(row["gold_marker_count"] for row in items)
        markers_found = sum(row["gold_markers_found_after"] for row in items)
        by_category[category] = {
            "trials": len(items),
            "mean_headroom_tokens_saved": _mean(saved_tokens),
            "mean_headroom_tokens_saved_pct": _mean(ratios),
            "min_headroom_tokens_saved_pct": round(min(ratios), 4),
            "max_headroom_tokens_saved_pct": round(max(ratios), 4),
            "mean_tiktoken_serialized_savings_pct": _mean(tiktoken_savings),
            "gold_markers_found": markers_found,
            "gold_markers_total": marker_count,
            "gold_marker_survival_pct": round(100.0 * markers_found / marker_count, 4) if marker_count else None,
            "trials_with_all_markers_surviving": sum(bool(row["all_gold_markers_survived"]) for row in items),
            "metric_status_counts": {
                status: sum(row["metric_status"] == status for row in items)
                for status in sorted({row["metric_status"] for row in items})
            },
        }
    all_ratios = [100.0 * row["headroom_compression_ratio"] for row in rows]
    all_markers = sum(row["gold_marker_count"] for row in rows)
    all_found = sum(row["gold_markers_found_after"] for row in rows)
    return {
        "schema_version": 1,
        "benchmark": "synthetic_headroom_tool_output_compression",
        "trials": len(rows),
        "variants_per_category": 5,
        "categories": by_category,
        "overall": {
            "mean_headroom_tokens_saved_pct": _mean(all_ratios),
            "min_headroom_tokens_saved_pct": round(min(all_ratios), 4) if all_ratios else None,
            "max_headroom_tokens_saved_pct": round(max(all_ratios), 4) if all_ratios else None,
            "gold_markers_found": all_found,
            "gold_markers_total": all_markers,
            "gold_marker_survival_pct": round(100.0 * all_found / all_markers, 4) if all_markers else None,
            "trials_with_all_markers_surviving": sum(bool(row["all_gold_markers_survived"]) for row in rows),
            "metric_status_counts": {
                status: sum(row["metric_status"] == status for row in rows)
                for status in sorted({row["metric_status"] for row in rows})
            },
        },
        "oracle_scope": (
            "Exact substring presence of the predetermined synthetic marker strings in the JSON-serialized "
            "message list before and after compression. It does not assess meaning, semantic correctness, "
            "other facts, task success, security, or provider behavior."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()

    versions = _versions()
    encoding = tiktoken.get_encoding(TOKENIZER_NAME)
    model_encoding = tiktoken.encoding_for_model(HEADROOM_MODEL_LABEL)
    if model_encoding.name != TOKENIZER_NAME:
        raise RuntimeError(
            f"Expected {HEADROOM_MODEL_LABEL} to map to {TOKENIZER_NAME}; got {model_encoding.name}"
        )

    rows: list[dict[str, Any]] = []
    full_rows: list[dict[str, Any]] = []
    for fixture in build_fixtures():
        metric, full = _run_trial(fixture, encoding)
        rows.append(metric)
        full_rows.append(full)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "trial-metrics.json", rows)
    _write_json(output_dir / "summary.json", _summarize(rows))
    with (output_dir / "trial-details.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in full_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    project_dir = Path(__file__).resolve().parent
    lock_bytes = (project_dir / "uv.lock").read_bytes()
    pyproject_bytes = (project_dir / "pyproject.toml").read_bytes()
    environment = {
        "schema_version": 1,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "uv_version": _uv_version(),
        "direct_package_versions": versions,
        "headroom_api": "headroom.compress",
        "headroom_model_label_for_local_token_counting": HEADROOM_MODEL_LABEL,
        "headroom_options": {
            "protect_recent": 0,
            "compress_user_messages": False,
            "kompress_model": "disabled",
        },
        "tiktoken_encoding": TOKENIZER_NAME,
        "model_label_encoding_check": model_encoding.name,
        "provider_api_calls": 0,
        "notes": [
            "The runner calls the local Headroom compression API and does not invoke an LLM provider client.",
            "kompress_model=disabled excludes the separately distributed Kompress model weights; Headroom's local pipeline remains enabled.",
            "The lockfile records the complete resolved dependency versions and package artifact hashes.",
            "No host-specific file paths, raw logs, or credentials are included in this manifest.",
        ],
        "source_hashes": {
            "run_benchmark.py": hashlib.sha256((project_dir / "run_benchmark.py").read_bytes()).hexdigest(),
            "fixtures.py": hashlib.sha256((project_dir / "fixtures.py").read_bytes()).hexdigest(),
            "pyproject.toml": hashlib.sha256(pyproject_bytes).hexdigest(),
            "uv.lock": hashlib.sha256(lock_bytes).hexdigest(),
        },
    }
    _write_json(output_dir / "environment.json", environment)

    summary = _summarize(rows)
    print(
        json.dumps(
            {
                "trials": summary["trials"],
                "overall": summary["overall"],
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
