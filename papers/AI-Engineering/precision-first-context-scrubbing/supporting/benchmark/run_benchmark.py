#!/usr/bin/env python3
"""Deterministic benchmark runner for Precision-First Context Scrubbing.

Evaluates:
1. Per-detector metrics over 101 labeled format-test and negative-control cases.
2. A pinned scanner snapshot against a naive regex baseline.
3. Serialized finding counts and token sizes on a safe all-negative workload.
4. Scan-call timings, bulk throughput, and overlength-line skip behavior.

The runner makes no live provider API calls. Wall-clock timings vary by environment.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SCANNER_SRC = HERE / "vendor" / "koality-pii-scanner" / "src"
sys.path.insert(0, str(SCANNER_SRC))

import tiktoken
import pii_scan
from pii_scan.rules import default_ruleset
from pii_scan.scanner import Config, run
from pii_scan.sarif import render_sarif

from fixtures import (
    CorpusCase,
    generate_synthetic_code_workload,
    get_naive_regex_rules,
    get_workload_ground_truth,
    load_corpus,
)

METRICS_DIR = HERE / "metrics"
SCANNER_COMMIT = "514f708e8890add75a963ff771245c1256394323"
HASHED_FILES = (
    "corpus/labeled.jsonl",
    "fixtures.py",
    "metrics/summary.json",
    "metrics/trial-metrics.json",
    "requirements.txt",
    "vendor/koality-pii-scanner/LICENSE",
    "vendor/koality-pii-scanner/src/pii_scan/__init__.py",
    "vendor/koality-pii-scanner/src/pii_scan/__main__.py",
    "vendor/koality-pii-scanner/src/pii_scan/cli.py",
    "vendor/koality-pii-scanner/src/pii_scan/exit_codes.py",
    "vendor/koality-pii-scanner/src/pii_scan/finding.py",
    "vendor/koality-pii-scanner/src/pii_scan/rules.py",
    "vendor/koality-pii-scanner/src/pii_scan/sarif.py",
    "vendor/koality-pii-scanner/src/pii_scan/scanner.py",
    "vendor/koality-pii-scanner/src/pii_scan/validators.py",
    "vendor/koality-pii-scanner/src/pii_scan/data/__init__.py",
    "vendor/koality-pii-scanner/src/pii_scan/data/default.yaml",
    "run-manifest.json",
    "run_benchmark.py",
    "verify_sha256_manifest.py",
)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

ENCODER = tiktoken.get_encoding("o200k_base")
EVALUATED_RULES = ("credit-card", "ssn-us", "email", "ipv4", "ipv6", "mac-address")


def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))


@dataclass
class ConfusionMatrix:
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float | None
    recall: float | None
    specificity: float | None
    f1: float | None


def compute_metrics(tp: int, fp: int, fn: int, tn: int) -> ConfusionMatrix:
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall)
        else None
    )
    return ConfusionMatrix(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=round(precision, 4) if precision is not None else None,
        recall=round(recall, 4) if recall is not None else None,
        specificity=round(specificity, 4) if specificity is not None else None,
        f1=round(f1, 4) if f1 is not None else None,
    )


def format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def run_deterministic_corpus_evaluation(cases: list[CorpusCase], ruleset) -> tuple[dict[str, ConfusionMatrix], float]:
    with tempfile.TemporaryDirectory() as td:
        corpus_file = Path(td) / "corpus.txt"
        corpus_file.write_text("".join(c.text + "\n" for c in cases), encoding="utf-8")

        t0 = time.perf_counter()
        result = run(Config(source=td, ruleset=ruleset))
        t1 = time.perf_counter()
        duration_ms = (t1 - t0) * 1000.0

    fired_by_line: dict[int, set[str]] = defaultdict(set)
    for finding in result.findings:
        rule = finding.rule_id.split(":", 1)[1] if ":" in finding.rule_id else finding.rule_id
        if rule in EVALUATED_RULES:
            fired_by_line[finding.line].add(rule)

    rule_metrics = {}
    for rule in EVALUATED_RULES:
        tp, fp, fn, tn = 0, 0, 0, 0
        for i, c in enumerate(cases):
            line_num = i + 1
            is_expected = rule in c.rules
            did_fire = rule in fired_by_line[line_num]
            if is_expected and did_fire:
                tp += 1
            elif not is_expected and did_fire:
                fp += 1
            elif is_expected and not did_fire:
                fn += 1
            else:
                tn += 1
        rule_metrics[rule] = compute_metrics(tp, fp, fn, tn)

    return rule_metrics, duration_ms


def run_naive_regex_evaluation(cases: list[CorpusCase]) -> tuple[dict[str, ConfusionMatrix], dict[str, list[str]]]:
    naive_rules = get_naive_regex_rules()
    rule_metrics = {}
    fp_samples: dict[str, list[str]] = defaultdict(list)

    for rule, pattern in naive_rules.items():
        tp, fp, fn, tn = 0, 0, 0, 0
        for c in cases:
            is_expected = rule in c.rules
            did_match = bool(pattern.search(c.text))
            if is_expected and did_match:
                tp += 1
            elif not is_expected and did_match:
                fp += 1
                if len(fp_samples[rule]) < 3:
                    fp_samples[rule].append(c.case_id)
            elif is_expected and not did_match:
                fn += 1
            else:
                tn += 1
        rule_metrics[rule] = compute_metrics(tp, fp, fn, tn)

    return rule_metrics, dict(fp_samples)


def run_context_window_bloat_benchmark(ruleset) -> dict[str, Any]:
    """Measure serialized findings on an all-negative synthetic control workload."""
    workload = generate_synthetic_code_workload()
    expected = get_workload_ground_truth()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel_path, content in workload.items():
            file_path = root / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        det_result = run(Config(source=td, ruleset=ruleset))
        det_findings = [
            finding
            for finding in det_result.findings
            if finding.rule_id.split(":", 1)[-1] in EVALUATED_RULES
        ]
        det_findings_dict = [finding.to_dict() for finding in det_findings]
        det_json_str = json.dumps(det_findings_dict, indent=2)
        det_sarif_str = render_sarif(det_findings, ruleset)
        det_json_tokens = count_tokens(det_json_str)
        det_sarif_tokens = count_tokens(det_sarif_str)

        naive_rules = get_naive_regex_rules()
        naive_findings = []
        for rel_path, content in workload.items():
            for line_idx, line in enumerate(content.splitlines(), start=1):
                for rule_name, pat in naive_rules.items():
                    for match in pat.finditer(line):
                        naive_findings.append({
                            "rule_id": f"naive:{rule_name}",
                            "file": rel_path,
                            "line": line_idx,
                            "summary": f"Detected {rule_name}",
                            "match": match.group(0),
                        })
        naive_json_str = json.dumps(naive_findings, indent=2)
        naive_json_tokens = count_tokens(naive_json_str)

    def key_for(finding) -> tuple[str, int, str]:
        rel_path = finding.file.replace("\\", "/")
        rule = finding.rule_id.split(":", 1)[-1]
        return (rel_path, finding.line, rule)

    det_keys = {key_for(finding) for finding in det_findings}
    naive_keys = {
        (item["file"], item["line"], item["rule_id"].split(":", 1)[-1])
        for item in naive_findings
    }
    det_tp = len(det_keys & expected)
    det_fp = len(det_keys - expected)
    det_fn = len(expected - det_keys)
    naive_tp = len(naive_keys & expected)
    naive_fp = len(naive_keys - expected)
    naive_fn = len(expected - naive_keys)
    false_positives_avoided = naive_fp - det_fp
    false_positive_reduction_pct = (
        false_positives_avoided / naive_fp * 100.0 if naive_fp else 0.0
    )
    tokens_saved = naive_json_tokens - det_json_tokens
    token_savings_pct = (
        tokens_saved / naive_json_tokens * 100.0 if naive_json_tokens else 0.0
    )

    return {
        "files_tested": len(workload),
        "ground_truth_scope": "all-negative; values are reserved, invalid, or documented test values",
        "expected_findings_count": len(expected),
        "deterministic_findings_count": len(det_findings),
        "deterministic_true_positives": det_tp,
        "deterministic_false_positives": det_fp,
        "deterministic_false_negatives": det_fn,
        "naive_findings_count": len(naive_keys),
        "naive_true_positives": naive_tp,
        "naive_false_positives": naive_fp,
        "naive_false_negatives": naive_fn,
        "false_positive_findings_avoided": false_positives_avoided,
        "false_positive_reduction_pct": round(false_positive_reduction_pct, 2),
        "deterministic_json_tokens": det_json_tokens,
        "deterministic_sarif_tokens": det_sarif_tokens,
        "naive_json_tokens": naive_json_tokens,
        "tokens_saved": tokens_saved,
        "token_savings_pct": round(token_savings_pct, 2),
    }


def run_throughput_and_line_limit_benchmark(ruleset) -> dict[str, Any]:
    """Measure scan-call timings and the configured overlength-line skip behavior."""
    normal_line = "const host = '127.0.0.1'; let port = 3000; // standard line\n"
    long_line = "var chunk = " + "'a' + " * 3500 + "'b';\n"

    with tempfile.TemporaryDirectory() as td:
        f_norm = Path(td) / "normal.ts"
        f_norm.write_text(normal_line * 100, encoding="utf-8")
        f_mini = Path(td) / "bundle.min.js"
        f_mini.write_text(long_line, encoding="utf-8")

        t0 = time.perf_counter()
        run(Config(source=str(f_norm), ruleset=ruleset))
        t1 = time.perf_counter()
        normal_duration_ms = (t1 - t0) * 1000.0

        t2 = time.perf_counter()
        res_mini = run(Config(source=str(f_mini), ruleset=ruleset))
        t3 = time.perf_counter()
        mini_duration_ms = (t3 - t2) * 1000.0
        overlength_line_skipped = any(
            error.startswith("MINIFIED_SKIP:") for error in res_mini.errors
        )
        if not overlength_line_skipped:
            raise RuntimeError("overlength-line fixture was not skipped")

        bulk_dir = Path(td) / "bulk"
        bulk_dir.mkdir()
        for i in range(50):
            lines = [
                f"// File {i} Line {j}: const test_value_{j} = {j*100};"
                for j in range(200)
            ]
            (bulk_dir / f"module_{i}.ts").write_text("\n".join(lines), encoding="utf-8")

        t_bulk_start = time.perf_counter()
        run(Config(source=str(bulk_dir), ruleset=ruleset))
        t_bulk_end = time.perf_counter()
        bulk_duration_s = t_bulk_end - t_bulk_start

    lines_scanned = 10000
    throughput_lines_sec = lines_scanned / bulk_duration_s if bulk_duration_s > 0 else 0.0
    return {
        "normal_file_100_lines_scan_call_ms": round(normal_duration_ms, 3),
        "overlength_line_24kb_scan_call_ms": round(mini_duration_ms, 3),
        "overlength_line_skipped": overlength_line_skipped,
        "bulk_files_count": 50,
        "bulk_lines_count": lines_scanned,
        "bulk_duration_sec": round(bulk_duration_s, 3),
        "throughput_lines_per_sec": round(throughput_lines_sec, 1),
        "limit": "The benchmark does not run an unbounded regex or measure ReDoS behavior.",
    }


def update_sha256_manifest() -> int:
    """Refresh hashes for the benchmark's inputs, code, and generated outputs."""
    manifest = {
        rel_path: hashlib.sha256((HERE / rel_path).read_bytes()).hexdigest()
        for rel_path in HASHED_FILES
    }
    manifest_path = HERE / "sha256-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(manifest)


def main() -> None:
    timestamp_utc = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    print("=" * 80)
    print("PRECISION-FIRST CONTEXT SCRUBBING: DETERMINISTIC BENCHMARK SUITE")
    print("=" * 80)

    cases = load_corpus()
    print(f"Loaded {len(cases)} documented synthetic test cases.")
    ruleset = default_ruleset()
    print(f"Loaded default ruleset with {len(ruleset.rules)} compiled detection rules.")

    print("\n[Phase 1] Evaluating deterministic scanner over labeled test cases...")
    det_metrics, det_scan_time_ms = run_deterministic_corpus_evaluation(cases, ruleset)
    print("\n[Phase 2] Evaluating naive regex baseline...")
    naive_metrics, fp_samples = run_naive_regex_evaluation(cases)
    print("\n[Phase 3] Evaluating the all-negative context workload...")
    context_metrics = run_context_window_bloat_benchmark(ruleset)
    print("\n[Phase 4] Measuring scan timings and line-limit skip behavior...")
    perf_metrics = run_throughput_and_line_limit_benchmark(ruleset)

    total_det_tp = sum(m.tp for m in det_metrics.values())
    total_det_fp = sum(m.fp for m in det_metrics.values())
    total_det_fn = sum(m.fn for m in det_metrics.values())
    total_naive_tp = sum(m.tp for m in naive_metrics.values())
    total_naive_fp = sum(m.fp for m in naive_metrics.values())
    total_naive_fn = sum(m.fn for m in naive_metrics.values())

    det_agg_prec = (
        total_det_tp / (total_det_tp + total_det_fp)
        if total_det_tp + total_det_fp else None
    )
    det_agg_recall = (
        total_det_tp / (total_det_tp + total_det_fn)
        if total_det_tp + total_det_fn else None
    )
    naive_agg_prec = (
        total_naive_tp / (total_naive_tp + total_naive_fp)
        if total_naive_tp + total_naive_fp else None
    )
    naive_agg_recall = (
        total_naive_tp / (total_naive_tp + total_naive_fn)
        if total_naive_tp + total_naive_fn else None
    )

    print("\n" + "=" * 80)
    print("EMPIRICAL COMPARISON: DETERMINISTIC SCANNER VS NAIVE REGEX BASELINE")
    print("=" * 80)
    print(f"{'Rule ID':<15} | {'Det Prec':<10} {'Det Rec':<10} {'Det FP':<8} | {'Naive Prec':<10} {'Naive Rec':<10} {'Naive FP':<8}")
    print("-" * 80)
    for rule in EVALUATED_RULES:
        dm = det_metrics[rule]
        nm = naive_metrics[rule]
        print(
            f"{rule:<15} | {format_metric(dm.precision):<10} {format_metric(dm.recall):<10} "
            f"{dm.fp:<8} | {format_metric(nm.precision):<10} "
            f"{format_metric(nm.recall):<10} {nm.fp:<8}"
        )
    print("-" * 80)
    print(
        f"{'OVERALL':<15} | {format_metric(det_agg_prec):<10} "
        f"{format_metric(det_agg_recall):<10} {total_det_fp:<8} | "
        f"{format_metric(naive_agg_prec):<10} {format_metric(naive_agg_recall):<10} "
        f"{total_naive_fp:<8}"
    )
    print("=" * 80)

    print("\n[All-Negative Context Workload]")
    print(
        f"  Naive false positives: {context_metrics['naive_false_positives']} "
        f"({context_metrics['naive_json_tokens']} JSON tokens)"
    )
    print(
        f"  Deterministic false positives: {context_metrics['deterministic_false_positives']} "
        f"({context_metrics['deterministic_json_tokens']} JSON tokens)"
    )
    print(
        f"  False positives avoided: {context_metrics['false_positive_findings_avoided']}"
    )
    print(
        f"  JSON token reduction: {context_metrics['tokens_saved']} "
        f"({context_metrics['token_savings_pct']}%)"
    )
    print("\n[Scan Timing and Line-Length Behavior]")
    print(
        f"  100-line scan call: "
        f"{perf_metrics['normal_file_100_lines_scan_call_ms']} ms"
    )
    print(
        f"  24KB overlength line scan call: "
        f"{perf_metrics['overlength_line_24kb_scan_call_ms']} ms "
        f"(skipped: {perf_metrics['overlength_line_skipped']})"
    )
    print(
        f"  Bulk throughput: {perf_metrics['throughput_lines_per_sec']} lines/sec "
        f"({perf_metrics['bulk_files_count']} files, {perf_metrics['bulk_duration_sec']}s)"
    )

    positive_counts = {
        rule: sum(rule in case.rules for case in cases)
        for rule in EVALUATED_RULES
    }
    environment = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "tiktoken_version": version("tiktoken"),
        "scanner_version": pii_scan.__version__,
    }
    summary_data = {
        "timestamp_utc": timestamp_utc,
        "environment": environment,
        "corpus_evaluation": {
            "corpus_cases_count": len(cases),
            "evaluated_detectors": list(EVALUATED_RULES),
            "positive_cases_by_detector": positive_counts,
            "positive_scope_note": (
                "Positive values are documented format-test markers, not live personal data. "
                "No positive SSN, email, IPv4, or IPv6 examples are included."
            ),
            "deterministic_scan_duration_ms": round(det_scan_time_ms, 3),
            "deterministic": {r: asdict(m) for r, m in det_metrics.items()},
            "naive": {r: asdict(m) for r, m in naive_metrics.items()},
            "aggregate": {
                "deterministic_precision": round(det_agg_prec, 4) if det_agg_prec is not None else None,
                "deterministic_recall": round(det_agg_recall, 4) if det_agg_recall is not None else None,
                "deterministic_false_positives": total_det_fp,
                "naive_precision": round(naive_agg_prec, 4) if naive_agg_prec is not None else None,
                "naive_recall": round(naive_agg_recall, 4) if naive_agg_recall is not None else None,
                "naive_false_positives": total_naive_fp,
            },
            "naive_false_positive_sample_case_ids": fp_samples,
        },
        "context_bloat_benchmark": context_metrics,
        "throughput_benchmark": perf_metrics,
    }
    (METRICS_DIR / "summary.json").write_text(
        json.dumps(summary_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    trial_data = {
        "det_metrics": {r: asdict(m) for r, m in det_metrics.items()},
        "naive_metrics": {r: asdict(m) for r, m in naive_metrics.items()},
        "context_metrics": context_metrics,
        "perf_metrics": perf_metrics,
    }
    (METRICS_DIR / "trial-metrics.json").write_text(
        json.dumps(trial_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest_data = {
        "benchmark": "Precision-First Context Scrubbing Deterministic Benchmark",
        "timestamp_utc": timestamp_utc,
        "scanner_repository": "https://github.com/Koality-Assured/koality-pii-scanner",
        "scanner_commit": SCANNER_COMMIT,
        "scanner_version": pii_scan.__version__,
        "scanner_source": "vendored MIT-licensed package snapshot under vendor/koality-pii-scanner/",
        "python_version": platform.python_version(),
        "tiktoken_version": version("tiktoken"),
        "corpus_cases_count": len(cases),
        "evaluated_rules_count": len(EVALUATED_RULES),
        "context_workload_ground_truth": "all-negative safe test controls",
        "files_generated": [
            "metrics/trial-metrics.json",
            "metrics/summary.json",
            "run-manifest.json",
            "sha256-manifest.json",
        ],
        "zero_live_provider_api_calls": True,
        "tokenizer_note": "The tokenizer may download its encoding data on first use if it is not cached.",
        "status": "completed",
    }
    (HERE / "run-manifest.json").write_text(
        json.dumps(manifest_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("\nUpdated summary.json, trial-metrics.json, run-manifest.json, and SHA-256 manifest.")
    print(f"Verified file set contains {update_sha256_manifest()} entries.")


if __name__ == "__main__":
    main()
