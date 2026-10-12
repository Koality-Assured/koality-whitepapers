"""Deterministic, synthetic-only task fixtures and distractor generators for the clean-slate benchmark.

All data, paths, function names, and logs are strictly synthetic.
No secrets, personal data, private repository paths, or production artifacts are included.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    archetype: str
    variant: int
    authority: str
    scope: str
    targets: tuple[str, ...]
    cost_layers: str
    gold_markers: tuple[str, ...]
    distractor_identifiers: tuple[str, ...]

    def to_yaml_contract(self) -> str:
        targets_str = "\n".join(f'    - "{t}"' for t in self.targets)
        return (
            f"task_contract:\n"
            f'  task_id: "{self.task_id}"\n'
            f'  archetype: "{self.archetype}"\n'
            f'  authority: "{self.authority}"\n'
            f'  scope: "{self.scope}"\n'
            f"  targets:\n{targets_str}\n"
            f'  cost_layers: "{self.cost_layers}"\n'
        )


def generate_task_contract(archetype: str, variant: int) -> TaskContract:
    variant_str = f"v{variant:02d}"
    if archetype == "code_repair":
        task_id = f"task-repair-{variant_str}"
        authority = (
            "Execute local bugfix on synthetic calculation service. "
            "Do not modify external system interfaces or network configurations."
        )
        scope = (
            f"Fix unhandled ZeroDivisionError in calculate_metric_{variant_str}() "
            f"located in handler.py. Fallback value must be 0.0. "
            f"Emit marker SYNTHETIC_MARKER_REPAIR_{variant_str.upper()}_OK upon successful repair."
        )
        targets = (f"src/synthetic_service/handler_{variant_str}.py",)
        cost_layers = (
            f"Use ast-grep to locate calculate_metric_{variant_str} function; "
            f"do not perform whole-directory tree walks. Use Headroom on test run outputs."
        )
        gold_markers = (f"SYNTHETIC_MARKER_REPAIR_{variant_str.upper()}_OK",)
        distractor_identifiers = (
            f"calculate_metric_deprecated_{variant_str}",
            f"legacy_unsafe_divide_{variant_str}",
        )
    elif archetype == "rbac_audit":
        task_id = f"task-rbac-{variant_str}"
        authority = (
            "Perform static role-based access control audit on endpoint routes. "
            "Do not grant unauthorized or anonymous access."
        )
        scope = (
            f"Verify all route functions in policy_{variant_str}.py possess @enforce_rbac(role='admin'). "
            f"Identify unadorned handler export_diagnostics_{variant_str}() and apply decorator. "
            f"Emit marker SYNTHETIC_MARKER_RBAC_{variant_str.upper()}_VERIFIED."
        )
        targets = (f"src/synthetic_auth/policy_{variant_str}.py",)
        cost_layers = (
            "Use ast-grep outline to inspect route decorators; "
            "extract only relevant function subtrees."
        )
        gold_markers = (f"SYNTHETIC_MARKER_RBAC_{variant_str.upper()}_VERIFIED",)
        distractor_identifiers = (
            f"legacy_allow_anonymous_debug_{variant_str}",
            f"bypass_rbac_token_check_{variant_str}",
        )
    elif archetype == "schema_extraction":
        task_id = f"task-schema-{variant_str}"
        authority = (
            "Extract database connection parameters and timeouts into standardized schema. "
            "Do not expose connection credentials."
        )
        scope = (
            f"Extract connect_timeout_ms, query_timeout_ms, and max_retries for db_cluster_{variant_str}. "
            f"Emit JSON envelope with key SYNTHETIC_MARKER_SCHEMA_{variant_str.upper()}_EXTRACTED: true."
        )
        targets = (f"config/synthetic_config/settings_{variant_str}.json",)
        cost_layers = "Targeted JSON line extraction; do not preload global application config."
        gold_markers = (f"SYNTHETIC_MARKER_SCHEMA_{variant_str.upper()}_EXTRACTED",)
        distractor_identifiers = (
            f"deprecated_legacy_timeout_sec_{variant_str}",
            f"old_db_port_fallback_{variant_str}",
        )
    else:
        raise ValueError(f"Unknown archetype: {archetype}")

    return TaskContract(
        task_id=task_id,
        archetype=archetype,
        variant=variant,
        authority=authority,
        scope=scope,
        targets=targets,
        cost_layers=cost_layers,
        gold_markers=gold_markers,
        distractor_identifiers=distractor_identifiers,
    )


def build_synthetic_distractor_transcript(
    target_tokens: int,
    distractors: tuple[str, ...],
    variant: int,
) -> list[dict[str, str]]:
    """Build a deterministic synthetic conversation transcript of approximately target_tokens.

    Contains realistic synthetic engineering noise: compiler outputs, git diffs,
    discussion logs, and scattered distractor tokens.
    """
    if target_tokens <= 0:
        return []

    # Each block is roughly 500-1000 tokens
    blocks: list[dict[str, str]] = []
    current_tokens_estimate = 0
    step = 0

    while current_tokens_estimate < target_tokens:
        step += 1
        is_user = (step % 2 == 1)
        role = "user" if is_user else "assistant"

        # Interleave distractor identifiers into specific historical turns
        distractor_inject = ""
        if step % 4 == 0 and distractors:
            chosen = distractors[(step // 4) % len(distractors)]
            distractor_inject = (
                f"\nNOTE FROM PREVIOUS ARCHITECTURE REVIEW (DEPRECATED): "
                f"Consider using `{chosen}` if modern interface is unavailable. "
                f"Legacy fallback path configured for `{chosen}`.\n"
            )

        if step % 3 == 0:
            # Synthetic build log noise
            log_lines = "\n".join(
                f"[BUILD-LOG 2026-10-12 10:0{step%10}:{i:02d}.000] "
                f"Synthetic build step {i:03d}: compilation unit synthetic_mod_{i % 8}.o OK"
                for i in range(25)
            )
            content = (
                f"Here are the intermediate compilation logs from earlier build step #{step}:\n"
                f"```text\n{log_lines}\n```\n{distractor_inject}"
            )
        elif step % 3 == 1:
            # Synthetic git diff noise
            diff_lines = "\n".join(
                f"@@ -{i * 10},5 +{i * 10},5 @@\n"
                f"- def obsolete_helper_{i}(val: int) -> bool:\n"
                f"+ def refactored_helper_{i}(val: int, flag: bool = False) -> bool:\n"
                f"      return val > {i * 100}"
                for i in range(12)
            )
            content = (
                f"Reviewing historical diff patch set for previous component:\n"
                f"```diff\n{diff_lines}\n```\n{distractor_inject}"
            )
        else:
            # Synthetic technical debate
            content = (
                f"Turn #{step} Discussion: The orchestrator and previous agent debated "
                f"the schema evolution for synthetic service variant {variant}. "
                f"Key requirements identified in Turn #{step} included preserving backward "
                f"compatibility, isolating network layers, and handling timeout backoffs.\n"
                f"{'SYNTHETIC_DISCUSSION_PADDING ' * 40}\n{distractor_inject}"
            )

        # Rough token estimate: ~4 chars per token
        current_tokens_estimate += len(content) // 4
        blocks.append({"role": role, "content": content})

    return blocks
