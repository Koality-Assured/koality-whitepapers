#!/usr/bin/env python3
"""Offline benchmark runner for commit-bound proof gates and negative routing."""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from proof_gate import (  # noqa: E402
    classify_execution_tier,
    verify_ancestry_only,
    verify_naive_status_only,
    verify_strict_commit_bound,
)
from synthetic_repos import (  # noqa: E402
    get_proof_scenarios,
    get_routing_samples,
    materialize_scenario,
)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 4)
    idx = (len(sorted_values) - 1) * pct
    low = math.floor(idx)
    high = math.ceil(idx)
    if low == high:
        return round(sorted_values[low], 4)
    frac = idx - low
    return round(sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac, 4)


def _summarize_latencies(samples_ms: list[float]) -> dict[str, float]:
    ordered = sorted(samples_ms)
    return {
        "count": len(ordered),
        "min_ms": round(ordered[0], 4),
        "p50_ms": _percentile(ordered, 0.50),
        "mean_ms": round(statistics.mean(ordered), 4),
        "p95_ms": _percentile(ordered, 0.95),
        "max_ms": round(ordered[-1], 4),
    }


def _confusion_summary(rows: list[dict[str, Any]], pred_key: str, expected_key: str) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in rows:
        expected = bool(row[expected_key])
        predicted = bool(row[pred_key])
        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif not expected and not predicted:
            tn += 1
        else:
            fn += 1

    total = len(rows)
    neg_total = tn + fp
    pos_total = tp + fn
    return {
        "total_scenarios": total,
        "true_accept_tp": tp,
        "false_accept_fp": fp,
        "true_reject_tn": tn,
        "false_reject_fn": fn,
        "overall_accuracy_pct": round((tp + tn) / total * 100.0, 2) if total else 0.0,
        "fail_closed_rate_pct": round(tn / neg_total * 100.0, 2) if neg_total else 0.0,
        "false_accept_rate_pct": round(fp / neg_total * 100.0, 2) if neg_total else 0.0,
        "false_reject_rate_pct": round(fn / pos_total * 100.0, 2) if pos_total else 0.0,
    }


def _run_proof_gate_benchmark(iterations: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scenarios = get_proof_scenarios()
    scenario_records: list[dict[str, Any]] = []

    naive_latencies_all: list[float] = []
    ancestry_latencies_all: list[float] = []
    strict_latencies_all: list[float] = []

    with tempfile.TemporaryDirectory() as tmp:
        work_root = Path(tmp)
        for spec in scenarios:
            setup_start = time.perf_counter()
            ctx = materialize_scenario(spec, work_root)
            setup_ms = (time.perf_counter() - setup_start) * 1000.0

            naive_ms_runs: list[float] = []
            ancestry_ms_runs: list[float] = []
            strict_ms_runs: list[float] = []

            naive_res = None
            ancestry_res = None
            strict_res = None

            for _ in range(iterations):
                t0 = time.perf_counter()
                naive_res = verify_naive_status_only(ctx.proof_path)
                t1 = time.perf_counter()
                naive_ms_runs.append((t1 - t0) * 1000.0)

                t2 = time.perf_counter()
                ancestry_res = verify_ancestry_only(ctx.repo_dir, ctx.proof_path)
                t3 = time.perf_counter()
                ancestry_ms_runs.append((t3 - t2) * 1000.0)

                t4 = time.perf_counter()
                strict_res = verify_strict_commit_bound(
                    ctx.repo_dir,
                    ctx.proof_path,
                    expected_branch=ctx.expected_branch,
                )
                t5 = time.perf_counter()
                strict_ms_runs.append((t5 - t4) * 1000.0)

            assert naive_res is not None and ancestry_res is not None and strict_res is not None
            naive_latencies_all.extend(naive_ms_runs)
            ancestry_latencies_all.extend(ancestry_ms_runs)
            strict_latencies_all.extend(strict_ms_runs)

            scenario_records.append(
                {
                    "scenario_id": spec.scenario_id,
                    "category": spec.category,
                    "language": spec.language,
                    "description": spec.description,
                    "expected_pass": spec.expected_strict_pass,
                    "naive_passed": naive_res.passed,
                    "ancestry_passed": ancestry_res.passed,
                    "strict_passed": strict_res.passed,
                    "strict_reasons": list(strict_res.reasons),
                    "ancestry_reasons": list(ancestry_res.reasons),
                    "setup_ms": round(setup_ms, 4),
                    "naive_p50_ms": _percentile(sorted(naive_ms_runs), 0.50),
                    "ancestry_p50_ms": _percentile(sorted(ancestry_ms_runs), 0.50),
                    "strict_p50_ms": _percentile(sorted(strict_ms_runs), 0.50),
                    "strict_p95_ms": _percentile(sorted(strict_ms_runs), 0.95),
                }
            )

    by_category: dict[str, dict[str, Any]] = {}
    categories = sorted({row["category"] for row in scenario_records})
    for cat in categories:
        cat_rows = [row for row in scenario_records if row["category"] == cat]
        by_category[cat] = {
            "count": len(cat_rows),
            "naive_passed_count": sum(1 for r in cat_rows if r["naive_passed"]),
            "ancestry_passed_count": sum(1 for r in cat_rows if r["ancestry_passed"]),
            "strict_passed_count": sum(1 for r in cat_rows if r["strict_passed"]),
            "expected_pass_count": sum(1 for r in cat_rows if r["expected_pass"]),
        }

    proof_summary = {
        "iterations_per_scenario": iterations,
        "total_scenarios": len(scenario_records),
        "positive_scenarios": sum(1 for r in scenario_records if r["expected_pass"]),
        "negative_scenarios": sum(1 for r in scenario_records if not r["expected_pass"]),
        "total_gate_evaluations_per_arm": len(scenario_records) * iterations,
        "arms": {
            "naive_status_only": {
                **_confusion_summary(scenario_records, "naive_passed", "expected_pass"),
                "latency": _summarize_latencies(naive_latencies_all),
            },
            "ancestry_only": {
                **_confusion_summary(scenario_records, "ancestry_passed", "expected_pass"),
                "latency": _summarize_latencies(ancestry_latencies_all),
            },
            "strict_commit_bound": {
                **_confusion_summary(scenario_records, "strict_passed", "expected_pass"),
                "latency": _summarize_latencies(strict_latencies_all),
            },
        },
        "by_category": by_category,
    }
    return proof_summary, scenario_records


def _run_routing_benchmark(iterations: int) -> dict[str, Any]:
    samples = get_routing_samples()
    classifiers = ("always_full_assurance", "naive_file_count", "deterministic_boundary")
    classifier_summaries: dict[str, Any] = {}
    sample_records: list[dict[str, Any]] = []

    per_sample_preds: dict[str, dict[str, Any]] = {s.sample_id: {} for s in samples}

    for clf in classifiers:
        latencies_ms: list[float] = []
        correct = 0
        over_escalated = 0
        under_escalated = 0
        direct_total = sum(1 for s in samples if s.expected_tier == "direct")
        full_total = sum(1 for s in samples if s.expected_tier == "full-assurance")

        for sample in samples:
            decision = None
            sample_runs: list[float] = []
            for _ in range(iterations):
                t0 = time.perf_counter()
                decision = classify_execution_tier(
                    sample.changed_files,
                    sample.diff_text,
                    has_regression_test=sample.has_regression_test,
                    classifier=clf,
                )
                t1 = time.perf_counter()
                sample_runs.append((t1 - t0) * 1000.0)
            latencies_ms.extend(sample_runs)
            assert decision is not None
            per_sample_preds[sample.sample_id][clf] = decision.to_dict()

            if decision.tier == sample.expected_tier:
                correct += 1
            elif sample.expected_tier == "direct" and decision.tier == "full-assurance":
                over_escalated += 1
            elif sample.expected_tier == "full-assurance" and decision.tier == "direct":
                under_escalated += 1

        classifier_summaries[clf] = {
            "total_samples": len(samples),
            "correct": correct,
            "accuracy_pct": round(correct / len(samples) * 100.0, 2),
            "over_escalated_count": over_escalated,
            "over_escalation_rate_pct": round(over_escalated / direct_total * 100.0, 2),
            "under_escalated_count": under_escalated,
            "under_escalation_rate_pct": round(under_escalated / full_total * 100.0, 2),
            "latency": _summarize_latencies(latencies_ms),
        }

    for sample in samples:
        sample_records.append(
            {
                "sample_id": sample.sample_id,
                "language": sample.language,
                "expected_tier": sample.expected_tier,
                "changed_files": sample.changed_files,
                "rationale": sample.rationale,
                "predictions": per_sample_preds[sample.sample_id],
            }
        )

    return {
        "iterations_per_sample": iterations,
        "total_samples": len(samples),
        "direct_samples": sum(1 for s in samples if s.expected_tier == "direct"),
        "full_assurance_samples": sum(1 for s in samples if s.expected_tier == "full-assurance"),
        "classifiers": classifier_summaries,
        "samples": sample_records,
    }


def _git_version() -> str:
    proc = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario_id",
        "category",
        "language",
        "expected_pass",
        "naive_passed",
        "ancestry_passed",
        "strict_passed",
        "setup_ms",
        "naive_p50_ms",
        "ancestry_p50_ms",
        "strict_p50_ms",
        "strict_p95_ms",
        "description",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Measured verification iterations per scenario (default: 10)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "metrics",
        help="Output directory for generated metrics artifacts",
    )
    args = parser.parse_args()
    if args.iterations < 1:
        raise ValueError("--iterations must be >= 1")

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    proof_summary, scenario_records = _run_proof_gate_benchmark(args.iterations)
    routing_results = _run_routing_benchmark(args.iterations)

    environment = {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "git_version": _git_version(),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    summary_payload = {
        "benchmark_id": "commit-bound-proof-gates-synthetic-v1",
        "environment": environment,
        "proof_gate_benchmark": proof_summary,
        "negative_routing_summary": {
            "total_samples": routing_results["total_samples"],
            "direct_samples": routing_results["direct_samples"],
            "full_assurance_samples": routing_results["full_assurance_samples"],
            "classifiers": routing_results["classifiers"],
        },
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out_dir / "trial-metrics.json").write_text(
        json.dumps(
            {
                "environment": environment,
                "iterations_per_scenario": args.iterations,
                "scenarios": scenario_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "routing-metrics.json").write_text(
        json.dumps(
            {
                "environment": environment,
                **routing_results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(out_dir / "matrix.csv", scenario_records)

    print(
        json.dumps(
            {
                "status": "OK",
                "total_scenarios": proof_summary["total_scenarios"],
                "iterations": args.iterations,
                "strict_accuracy_pct": proof_summary["arms"]["strict_commit_bound"]["overall_accuracy_pct"],
                "strict_fail_closed_pct": proof_summary["arms"]["strict_commit_bound"]["fail_closed_rate_pct"],
                "ancestry_fail_closed_pct": proof_summary["arms"]["ancestry_only"]["fail_closed_rate_pct"],
                "naive_fail_closed_pct": proof_summary["arms"]["naive_status_only"]["fail_closed_rate_pct"],
                "routing_accuracy_pct": routing_results["classifiers"]["deterministic_boundary"]["accuracy_pct"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
