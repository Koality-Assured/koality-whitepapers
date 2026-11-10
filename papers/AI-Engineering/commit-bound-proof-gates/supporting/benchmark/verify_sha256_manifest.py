#!/usr/bin/env python3
"""Verify or generate normalized-text SHA-256 digests for benchmark artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NORMALIZATION = "CRLF and CR line endings normalized to LF before hashing"
DEFAULT_MANIFEST = "sha256-manifest.json"
TRACKED_FILES = (
    "proof_gate.py",
    "synthetic_repos.py",
    "run_benchmark.py",
    "test_proof_gate.py",
    "metrics/summary.json",
    "metrics/trial-metrics.json",
    "metrics/routing-metrics.json",
    "metrics/blind-trial-results.json",
    "metrics/matrix.csv",
    "blind-trials/PROTOCOL.md",
    "blind-trials/ground-truth-rubric.json",
    "blind-trials/fixtures/trial_01_race_lease_go/go.mod",
    "blind-trials/fixtures/trial_01_race_lease_go/manager.go",
    "blind-trials/fixtures/trial_01_race_lease_go/manager_test.go",
    "blind-trials/fixtures/trial_02_stale_sha_gate_py/validator.py",
    "blind-trials/fixtures/trial_02_stale_sha_gate_py/test_repro.py",
    "blind-trials/fixtures/trial_03_path_boundary_js/exporter.mjs",
    "blind-trials/fixtures/trial_03_path_boundary_js/exporter.test.mjs",
    "blind-trials/fixtures/trial_04_silent_error_swallow_py/receipt_check.py",
    "blind-trials/fixtures/trial_04_silent_error_swallow_py/test_repro.py",
    "blind-trials/packets/blind/trial_01_race_lease_go.md",
    "blind-trials/packets/blind/trial_02_stale_sha_gate_py.md",
    "blind-trials/packets/blind/trial_03_path_boundary_js.md",
    "blind-trials/packets/blind/trial_04_silent_error_swallow_py.md",
    "blind-trials/packets/non_blind/trial_01_race_lease_go.md",
    "blind-trials/packets/non_blind/trial_02_stale_sha_gate_py.md",
    "blind-trials/packets/non_blind/trial_03_path_boundary_js.md",
    "blind-trials/packets/non_blind/trial_04_silent_error_swallow_py.md",
)


def normalized_bytes(path: Path) -> bytes:
    """Normalize CRLF and bare CR line endings to LF before hashing."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def generate_manifest(manifest_rel: Path) -> int:
    if manifest_rel.is_absolute():
        raise ValueError("Manifest path must be relative to benchmark directory")
    manifest_path = (HERE / manifest_rel).resolve()
    if HERE not in manifest_path.parents:
        raise ValueError("Manifest path must reside inside benchmark directory")

    entries: list[dict[str, str]] = []
    for rel in TRACKED_FILES:
        target = (HERE / rel).resolve()
        if not target.is_file():
            raise FileNotFoundError(f"Tracked benchmark artifact missing: {rel}")
        digest = hashlib.sha256(normalized_bytes(target)).hexdigest()
        entries.append({"path": rel, "sha256": digest})

    payload = {
        "hash_algorithm": "SHA-256",
        "hash_normalization": NORMALIZATION,
        "files": entries,
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(entries)} normalized-text SHA-256 digests to {manifest_path.name}.")
    return 0


def verify_manifest(manifest_rel: Path) -> int:
    if manifest_rel.is_absolute():
        raise ValueError("Manifest path must be relative to benchmark directory")
    manifest_path = (HERE / manifest_rel).resolve()
    if HERE not in manifest_path.parents or not manifest_path.is_file():
        raise ValueError(f"Manifest file not found inside benchmark directory: {manifest_rel}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("hash_algorithm") != "SHA-256":
        raise ValueError("Unsupported hash_algorithm in manifest")
    if manifest.get("hash_normalization") != NORMALIZATION:
        raise ValueError("Unsupported hash_normalization in manifest")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest files list is missing or empty")

    checked = 0
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Manifest entry missing string 'path'")
        rel = item["path"]
        expected = item.get("sha256")
        candidate = (HERE / rel).resolve()
        if candidate == manifest_path or HERE not in candidate.parents:
            raise ValueError(f"Manifest path escapes benchmark package: {rel!r}")
        if not candidate.is_file():
            raise ValueError(f"Missing manifest file: {rel}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid SHA-256 hex digest for {rel}")
        actual = hashlib.sha256(normalized_bytes(candidate)).hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {rel}: expected {expected}, got {actual}")
        checked += 1

    print(f"Verified {checked} files in {manifest_path.name} using normalized-text SHA-256.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(DEFAULT_MANIFEST))
    parser.add_argument("--write", action="store_true", help="Regenerate the manifest")
    args = parser.parse_args()
    try:
        if args.write:
            return generate_manifest(args.manifest)
        return verify_manifest(args.manifest)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"SHA-256 manifest error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
