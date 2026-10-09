"""Deterministic, synthetic-only tool-output fixtures for the paper benchmark."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    category: str
    variant: int
    messages: list[dict[str, object]]
    gold_markers: tuple[str, ...]


def _tool_message(fixture_id: str, content: str) -> list[dict[str, object]]:
    """Wrap only synthetic tool output; no prompts or real-world paths are used."""
    return [
        {
            "role": "tool",
            "tool_call_id": f"synthetic-{fixture_id}",
            "content": content,
        }
    ]


def _json_fixture(variant: int) -> Fixture:
    fixture_id = f"json-tool-v{variant:02d}"
    rows = [
        {
            "record_id": f"synthetic-record-{index:04d}",
            "group": f"synthetic-group-{index % 7}",
            "status": "SYNTHETIC_OK",
            "details": "SYNTHETIC_PADDING_SEGMENT " * 10,
        }
        for index in range(100 + variant * 16)
    ]
    marker_a = f"SYNTHETIC_GOLD_JSON_V{variant:02d}_ALPHA"
    marker_b = f"SYNTHETIC_GOLD_JSON_V{variant:02d}_OMEGA"
    rows.insert(
        len(rows) * (variant + 2) // 8,
        {
            "record_id": f"synthetic-gold-record-{variant:02d}",
            "group": "SYNTHETIC_GOLD_GROUP",
            "status": marker_a,
            "details": marker_b,
        },
    )
    content = json.dumps(
        {"fixture": "SYNTHETIC_JSON_TOOL_OUTPUT", "records": rows},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return Fixture(
        fixture_id=fixture_id,
        category="json_tool_output",
        variant=variant,
        messages=_tool_message(fixture_id, content),
        gold_markers=(marker_a, marker_b),
    )


def _build_log_fixture(variant: int) -> Fixture:
    fixture_id = f"build-log-v{variant:02d}"
    lines = [
        "INFO SYNTHETIC_BUILD "
        f"unit=synthetic-unit-{index:04d} result=SYNTHETIC_OK "
        f"trace=SYNTHETIC_TRACE_{index % 9} "
        + "SYNTHETIC_LOG_PADDING " * 8
        for index in range(240 + variant * 24)
    ]
    marker = f"SYNTHETIC_GOLD_BUILD_ERROR_V{variant:02d}"
    error_line = (
        f"ERROR {marker} code=SYNTHETIC_ERR_{variant + 100:03d} "
        f"unit=synthetic-unit-{variant + 30:04d}"
    )
    lines.insert(len(lines) * (variant + 2) // 8, error_line)
    content = "\n".join(lines)
    return Fixture(
        fixture_id=fixture_id,
        category="build_log_output",
        variant=variant,
        messages=_tool_message(fixture_id, content),
        gold_markers=(marker,),
    )


def _grep_fixture(variant: int) -> Fixture:
    fixture_id = f"grep-hit-v{variant:02d}"
    hits = [
        (
            f"synthetic/src/module-{index % 8}/file-{index:04d}.py:"
            f"{10 + index % 61}: SYNTHETIC_MATCH symbol=synthetic_name_{index % 6} "
            + "detail=SYNTHETIC_GREP_PADDING " * 3
        )
        for index in range(160 + variant * 20)
    ]
    marker_a = f"SYNTHETIC_GOLD_GREP_V{variant:02d}_ALPHA"
    marker_b = f"SYNTHETIC_GOLD_GREP_V{variant:02d}_OMEGA"
    hits.insert(
        len(hits) * (variant + 2) // 8,
        f"synthetic/src/gold/file-{variant:02d}.py:7: "
        f"SYNTHETIC_MATCH symbol={marker_a} detail={marker_b}",
    )
    content = "\n".join(hits)
    return Fixture(
        fixture_id=fixture_id,
        category="grep_hit_output",
        variant=variant,
        messages=_tool_message(fixture_id, content),
        gold_markers=(marker_a, marker_b),
    )


def build_fixtures() -> list[Fixture]:
    """Return exactly five numbered deterministic variants per fixture family."""
    builders = (_json_fixture, _build_log_fixture, _grep_fixture)
    return [builder(variant) for builder in builders for variant in range(5)]
