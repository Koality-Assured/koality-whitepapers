#!/usr/bin/env python3
"""Verifies SHA-256 integrity of benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "sha256-manifest.json"


def main() -> None:
    if not MANIFEST_FILE.exists():
        print("ERROR: sha256-manifest.json not found.", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest: dict[str, str] = json.load(f)

    failures = 0
    checked = 0

    for rel_path, expected_hash in manifest.items():
        if rel_path == "sha256-manifest.json":
            continue
        file_path = HERE / rel_path
        if not file_path.exists():
            print(f"MISSING: {rel_path}", file=sys.stderr)
            failures += 1
            continue

        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            print(f"HASH MISMATCH: {rel_path} (expected {expected_hash[:8]}..., got {actual_hash[:8]}...)", file=sys.stderr)
            failures += 1
        else:
            checked += 1

    if failures == 0:
        print(f"Integrity check passed! {checked} files verified against SHA-256 manifest.")
        sys.exit(0)
    else:
        print(f"Integrity check failed with {failures} error(s).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
