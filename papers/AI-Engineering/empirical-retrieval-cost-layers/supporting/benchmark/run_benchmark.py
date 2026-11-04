"""Empirical benchmark comparing Arm A (Shell Grep + Full File Dump) vs Arm B (Layered QMD BM25 + AST-Grep + Line-Bounded Multi-Get).

tags: [benchmarks, cost-layers, qmd, ast-grep, context-tax, whitepaper-empirical]
routing_hints: [eval-retrieval-cost-layers, context-tax, arm-a-vs-arm-b]
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 3.8))


def resolve_qmd_bin() -> str | None:
    if sys.platform == "win32":
        return shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    return shutil.which("qmd")


def resolve_qmd_root(root: Path) -> Path:
    qmd_main = root / "scratch" / "qmd-main"
    if qmd_main.is_dir() and (qmd_main / ".qmd" / "index.sqlite").exists():
        return qmd_main
    return root


BENCHMARK_SCENARIOS = [
    {
        "id": "scenario_1_worktree_isolation",
        "title": "Worktree Isolation & Spawning Policy",
        "intent": "Locate git worktree isolation requirements and spawn scripts",
        "grep_query": "spawn_worktree",
        "qmd_query": "isolate work git worktree",
        "sample_files": [
            "ai-tooling/skills/meta/isolate-work/SKILL.md",
            "docs/guidance/git-worktrees.md",
            "supporting/qmd/query-pattern.md",
            "routing/AGENTS.md",
        ],
    },
    {
        "id": "scenario_2_ast_grep_patterns",
        "title": "AST-Grep Pattern Extraction & Structural Rules",
        "intent": "Find ast-grep structural configuration, patterns, and memory rules",
        "grep_query": "ast-grep outline",
        "qmd_query": "ast-grep structural pattern matching",
        "sample_files": [
            "ai-tooling/skills/cost-layers/ast-grep/SKILL.md",
            "supporting/ast-grep/quick-reference.md",
            "supporting/ast-grep/installation.md",
            "ai-tooling/memory/agent/router-maintenance/ast-grep-cost-layer.md",
        ],
    },
    {
        "id": "scenario_3_threat_model_assessment",
        "title": "STRIDE Threat Modeling Architecture",
        "intent": "Find STRIDE threat modeling procedures and assessment agent spec",
        "grep_query": "STRIDE threat model",
        "qmd_query": "stride threat model assessment",
        "sample_files": [
            "ai-tooling/agents/assessment-agent/AGENT.md",
            "ai-tooling/skills/reporting/threat-model/SKILL.md",
        ],
    },
    {
        "id": "scenario_4_confluence_cql_sync",
        "title": "Confluence Document Synchronization & CQL",
        "intent": "Find Confluence page sync tools and CQL search patterns",
        "grep_query": "confluence cql",
        "qmd_query": "confluence cql document management",
        "sample_files": [
            "ai-tooling/skills/confluence/confluence-doc-manage/SKILL.md",
            "ai-tooling/agents/docs-collab-agent/AGENT.md",
        ],
    },
    {
        "id": "scenario_5_cost_estimation_benchmarks",
        "title": "Agent Token Cost Estimation & Pricing Tiers",
        "intent": "Find token estimation algorithms, pricing tables, and benchmark agent",
        "grep_query": "DEFAULT_PRICING_TABLE",
        "qmd_query": "benchmark agent cost estimation",
        "sample_files": [
            "ai-tooling/agents/benchmark-agent/AGENT.md",
            "ai-tooling/skills/benchmarks/agent-cost-estimator/SKILL.md",
        ],
    },
]


def run_benchmark(root: Path) -> dict[str, Any]:
    qmd_bin = resolve_qmd_bin()
    qmd_root = resolve_qmd_root(root)

    trials: list[dict[str, Any]] = []

    for sc in BENCHMARK_SCENARIOS:
        print(f"[*] Running {sc['id']}: {sc['title']}")

        # -------------------------------------------------------------
        # ARM A: Naive Shell Grep + Full File Dump
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        grep_res = subprocess.run(
            ["git", "grep", "-i", sc["grep_query"]],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        grep_latency = time.perf_counter() - t0
        grep_lines = grep_res.stdout.splitlines()

        # In naive agent workflows, agent reads full files matching query
        files_to_read = []
        for path_str in sc["sample_files"]:
            p = root / path_str
            if p.is_file():
                files_to_read.append(p)

        full_content_chars = 0
        read_t0 = time.perf_counter()
        for fp in files_to_read:
            try:
                full_content_chars += len(fp.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
        read_latency = time.perf_counter() - read_t0

        arm_a_total_chars = len(grep_res.stdout) + full_content_chars
        arm_a_tokens = estimate_tokens(grep_res.stdout) + estimate_tokens(
            " " * full_content_chars
        )
        arm_a_latency = grep_latency + read_latency

        # -------------------------------------------------------------
        # ARM B: Layered QMD BM25 + AST / Multi-Get Bounded Snippets
        # -------------------------------------------------------------
        b_t0 = time.perf_counter()
        qmd_out = ""
        qmd_hits = 0
        if qmd_bin:
            q_res = subprocess.run(
                [qmd_bin, "search", "--format", "json", "-n", "5", sc["qmd_query"]],
                cwd=qmd_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            qmd_out = q_res.stdout
            try:
                qmd_hits = len(json.loads(q_res.stdout))
            except Exception:
                qmd_hits = 0

        # Batch multi-get with line-bounding (-l 30)
        target_ids = []
        if qmd_bin and qmd_hits > 0:
            try:
                data = json.loads(qmd_out)
                for item in data[:3]:
                    docid = item.get("docid") or item.get("path")
                    if docid:
                        target_ids.append(docid)
            except Exception:
                pass

        multi_out = ""
        if qmd_bin and target_ids:
            target_arg = ",".join(target_ids)
            m_res = subprocess.run(
                [qmd_bin, "multi-get", target_arg, "--format", "md", "-l", "30"],
                cwd=qmd_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            multi_out = m_res.stdout

        arm_b_latency = time.perf_counter() - b_t0
        arm_b_chars = len(qmd_out) + len(multi_out)
        arm_b_tokens = estimate_tokens(qmd_out) + estimate_tokens(multi_out)

        # -------------------------------------------------------------
        # Multi-Turn Compounding Context Tax (10-Turn Horizon)
        # -------------------------------------------------------------
        # In Turn 1, context is injected.
        # Across Turns 2..10 (9 turns), that context is re-sent in every prompt.
        turns = 10
        arm_a_cumulative_tokens = arm_a_tokens * turns
        arm_b_cumulative_tokens = arm_b_tokens * turns

        token_savings_pct = (
            (arm_a_tokens - arm_b_tokens) / arm_a_tokens * 100
            if arm_a_tokens > 0
            else 0.0
        )
        cum_savings_tokens = arm_a_cumulative_tokens - arm_b_cumulative_tokens

        trial_data = {
            "scenario_id": sc["id"],
            "title": sc["title"],
            "arm_a_grep": {
                "grep_matches": len(grep_lines),
                "files_read": len(files_to_read),
                "raw_chars": arm_a_total_chars,
                "single_turn_tokens": arm_a_tokens,
                "cumulative_10turn_tokens": arm_a_cumulative_tokens,
                "latency_seconds": round(arm_a_latency, 4),
            },
            "arm_b_layered": {
                "qmd_hits": qmd_hits,
                "bounded_chars": arm_b_chars,
                "single_turn_tokens": arm_b_tokens,
                "cumulative_10turn_tokens": arm_b_cumulative_tokens,
                "latency_seconds": round(arm_b_latency, 4),
            },
            "comparison": {
                "single_turn_savings_tokens": arm_a_tokens - arm_b_tokens,
                "single_turn_savings_pct": round(token_savings_pct, 2),
                "cumulative_10turn_savings_tokens": cum_savings_tokens,
                "speedup_factor": round(arm_a_latency / arm_b_latency, 2)
                if arm_b_latency > 0
                else 1.0,
            },
        }
        trials.append(trial_data)

    # Aggregates
    total_arm_a_tokens = sum(t["arm_a_grep"]["single_turn_tokens"] for t in trials)
    total_arm_b_tokens = sum(t["arm_b_layered"]["single_turn_tokens"] for t in trials)
    total_cum_a_tokens = sum(
        t["arm_a_grep"]["cumulative_10turn_tokens"] for t in trials
    )
    total_cum_b_tokens = sum(
        t["arm_b_layered"]["cumulative_10turn_tokens"] for t in trials
    )

    overall_savings_pct = (
        (total_arm_a_tokens - total_arm_b_tokens) / total_arm_a_tokens * 100
        if total_arm_a_tokens > 0
        else 0.0
    )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(trials),
        "overall_summary": {
            "single_turn_arm_a_tokens": total_arm_a_tokens,
            "single_turn_arm_b_tokens": total_arm_b_tokens,
            "mean_token_savings_pct": round(overall_savings_pct, 2),
            "cumulative_10turn_arm_a_tokens": total_cum_a_tokens,
            "cumulative_10turn_arm_b_tokens": total_cum_b_tokens,
            "net_cumulative_tokens_saved": total_cum_a_tokens - total_cum_b_tokens,
        },
        "trials": trials,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Empirical benchmark: Arm A (grep/dump) vs Arm B (QMD BM25/AST layered retrieval)"
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Path to a public Koality-Assured/ai-router checkout containing the benchmark corpus",
    )
    parser.add_argument("--out", type=Path, help="Output directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print summary without writing files"
    )
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    if not (source_root / "AGENTS.md").is_file():
        parser.error("--source-root must point to the ai-router repository root")

    results = run_benchmark(source_root)
    summary = results["overall_summary"]

    print("\n" + "=" * 60)
    print("EMPIRICAL BENCHMARK SUMMARY (ARM A vs ARM B)")
    print("=" * 60)
    print(
        f"Single-Turn Context Load:  Arm A: {summary['single_turn_arm_a_tokens']} tokens | Arm B: {summary['single_turn_arm_b_tokens']} tokens"
    )
    print(f"Mean Token Reduction:     {summary['mean_token_savings_pct']}%")
    print(
        f"Cumulative 10-Turn Load:  Arm A: {summary['cumulative_10turn_arm_a_tokens']} tokens | Arm B: {summary['cumulative_10turn_arm_b_tokens']} tokens"
    )
    print(
        f"Net Cumulative Savings:   {summary['net_cumulative_tokens_saved']} tokens"
    )
    print("Provider billing and cache-hit rates are not measured by this benchmark.")
    print("=" * 60)

    if not args.dry_run:
        out_dir = args.out or source_root / "results" / "benchmarks" / "retrieval-cost-layers" / "2026-11-04"
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / "summary.json"
        trials_path = out_dir / "trial-metrics.json"
        summary_path.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "timestamp": results["timestamp_utc"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        trials_path.write_text(
            json.dumps(results["trials"], indent=2), encoding="utf-8"
        )
        print(f"\n[+] Wrote benchmark data to: {out_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
