#!/usr/bin/env python3
"""Verify empirical metric traceability between whitepapers and benchmark source data."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_clean_slate_metrics() -> list[str]:
    errors: list[str] = []
    base_dir = REPO_ROOT / "papers/AI-Engineering/clean-slate-specialist-context"
    summary_path = base_dir / "supporting/benchmark/metrics/summary.json"
    paper_path = base_dir / "PAPER.md"

    if not summary_path.is_file():
        return [f"Missing metric summary file: {summary_path}"]
    if not paper_path.is_file():
        return [f"Missing paper file: {paper_path}"]

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Could not parse {summary_path}: {exc}"]

    # Verify key fields
    try:
        token_reduction = data["key_findings"]["token_reduction_vs_fork_60k_pct"]
        clean_mean = data["by_condition"]["clean_slate"]["mean_cumulative_input_tokens"]
        fork60_mean = data["by_condition"]["fork_60k"]["mean_cumulative_input_tokens"]
        clean_oracle = data["by_condition"]["clean_slate"]["oracle_pass_rate_pct"]
        clean_collision = data["by_condition"]["clean_slate"]["distractor_collision_rate_pct"]
        fork60_collision = data["by_condition"]["fork_60k"]["distractor_collision_rate_pct"]
        fork60_oracle = data["by_condition"]["fork_60k"]["oracle_pass_rate_pct"]
        total_trials = data["total_trials"]
        task_variants = data["task_variants"]
    except KeyError as exc:
        return [f"{summary_path}: Missing expected key {exc}"]

    # Numerical expectations
    if not math.isclose(token_reduction, 99.722, abs_tol=0.01):
        errors.append(f"Unexpected token reduction in {summary_path}: {token_reduction}")
    if clean_mean != 655.33:
        errors.append(f"Unexpected clean_slate mean tokens: {clean_mean}")
    if fork60_mean != 235765.73:
        errors.append(f"Unexpected fork_60k mean tokens: {fork60_mean}")
    if clean_oracle != 100.0 or clean_collision != 0.0:
        errors.append("Unexpected clean_slate pass/collision rates")
    if fork60_collision != 46.67 or fork60_oracle != 53.33:
        errors.append("Unexpected fork_60k collision/pass rates")
    if total_trials != 75 or task_variants != 15:
        errors.append("Unexpected trials/variants count")

    # Paper text check
    paper_text = paper_path.read_text(encoding="utf-8")
    for cited in ["99.7220%", "655.33", "235,765.73", "100.0%", "53.33%", "46.67%"]:
        if cited not in paper_text:
            errors.append(f"PAPER.md does not cite expected headline figure: {cited}")

    return errors


def check_context_efficiency_metrics() -> list[str]:
    errors: list[str] = []
    base_dir = REPO_ROOT / "papers/AI-Engineering/context-efficiency-methods"
    summary_path = base_dir / "supporting/benchmark/metrics/summary.json"
    tooling_path = base_dir / "supporting/benchmark/metrics/tooling-suite-results.json"
    paper_path = base_dir / "PAPER.md"

    if not summary_path.is_file():
        return [f"Missing metric summary file: {summary_path}"]
    if not tooling_path.is_file():
        return [f"Missing tooling results file: {tooling_path}"]
    if not paper_path.is_file():
        return [f"Missing paper file: {paper_path}"]

    try:
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        tooling_data = json.loads(tooling_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Failed to parse JSON metrics: {exc}"]

    # Headroom summary checks
    try:
        headroom_mean = summary_data["overall"]["mean_headroom_tokens_saved_pct"]
        markers_found = summary_data["overall"]["gold_markers_found"]
        markers_total = summary_data["overall"]["gold_markers_total"]
        trials = summary_data["trials"]
        build_log = summary_data["categories"]["build_log_output"]["mean_headroom_tokens_saved_pct"]
        grep_hit = summary_data["categories"]["grep_hit_output"]["mean_headroom_tokens_saved_pct"]
        json_tool = summary_data["categories"]["json_tool_output"]["mean_headroom_tokens_saved_pct"]
    except KeyError as exc:
        errors.append(f"{summary_path}: Missing expected key {exc}")
    else:
        if headroom_mean != 86.53 or markers_found != 25 or markers_total != 25 or trials != 15:
            errors.append(f"Unexpected values in Headroom summary: {summary_data['overall']}")
        if not math.isclose(build_log, 97.52, abs_tol=0.01):
            errors.append(f"Unexpected build_log mean: {build_log}")
        if not math.isclose(grep_hit, 97.16, abs_tol=0.01):
            errors.append(f"Unexpected grep_hit mean: {grep_hit}")
        if not math.isclose(json_tool, 64.91, abs_tol=0.01):
            errors.append(f"Unexpected json_tool mean: {json_tool}")

    # Tooling suite checks
    try:
        qmd_correct = tooling_data["qmd"]["top_1_correct"]
        qmd_reduction = tooling_data["qmd"]["mean_selected_source_reduction_percent"]
        ast_reduction = tooling_data["ast_grep"]["result"]["byte_reduction_percent"]
        ast_markers = tooling_data["ast_grep"]["result"]["gold_markers_retained"]
        ast_selected = tooling_data["ast_grep"]["result"]["selected_bytes"]
        ast_source = tooling_data["ast_grep"]["result"]["source_bytes"]
        web_reduction = tooling_data["webfetch"]["mean_byte_reduction_percent"]
        web_markers = tooling_data["webfetch"]["gold_markers_retained"]
        prefix_bytes = tooling_data["prompt_prefix"]["result"]["declared_static_prefix_bytes"]
    except KeyError as exc:
        errors.append(f"{tooling_path}: Missing expected key {exc}")
    else:
        if qmd_correct != "4/4" or not math.isclose(qmd_reduction, 80.97, abs_tol=0.01):
            errors.append(f"Unexpected QMD results: {qmd_correct}, {qmd_reduction}")
        if ast_markers != "3/3" or ast_selected != 282 or ast_source != 758 or not math.isclose(ast_reduction, 62.80, abs_tol=0.01):
            errors.append(f"Unexpected ast-grep results")
        if web_markers != "15/15" or not math.isclose(web_reduction, 85.86, abs_tol=0.01):
            errors.append(f"Unexpected webfetch results: {web_markers}, {web_reduction}")
        if prefix_bytes != 216:
            errors.append(f"Unexpected prefix bytes: {prefix_bytes}")

    # Paper text check
    paper_text = paper_path.read_text(encoding="utf-8")
    for cited in ["86.53%", "80.97%", "62.80%", "85.86%", "216"]:
        if cited not in paper_text:
            errors.append(f"PAPER.md does not cite expected headline figure: {cited}")

    return errors


def main() -> int:
    total_errors: list[str] = []

    print("Checking clean-slate specialist context metrics traceability...")
    errs1 = check_clean_slate_metrics()
    if errs1:
        total_errors.extend(errs1)
    else:
        print("  OK: clean-slate-specialist-context metrics fully verified.")

    print("Checking context-efficiency-methods metrics traceability...")
    errs2 = check_context_efficiency_metrics()
    if errs2:
        total_errors.extend(errs2)
    else:
        print("  OK: context-efficiency-methods metrics fully verified.")

    if total_errors:
        print(f"\nTraceability verification failed with {len(total_errors)} errors:", file=sys.stderr)
        for err in total_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nAll whitepaper headline metrics successfully traced to benchmark JSON data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
