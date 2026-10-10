#!/usr/bin/env python3
"""Verify a public benchmark package's normalized-text SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
NORMALIZATION = "CRLF and CR line endings normalized to LF before hashing"


def normalized_bytes(path: Path) -> bytes:
    """Normalize CRLF and bare CR line endings to LF before hashing."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def manifest_entries(files: object) -> list[tuple[str, str]]:
    if isinstance(files, dict):
        return list(files.items())
    if isinstance(files, list):
        entries: list[tuple[str, str]] = []
        for item in files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise ValueError("Manifest file list must contain path/digest objects")
            entries.append((item["path"], item.get("sha256")))
        return entries
    raise ValueError("Manifest has no supported file digest mapping")


def verify(requested_manifest: Path) -> int:
    if requested_manifest.is_absolute():
        raise ValueError("Manifest path must be relative to the benchmark package")
    manifest_path = (HERE / requested_manifest).resolve()
    if HERE not in manifest_path.parents or not manifest_path.is_file():
        raise ValueError("Manifest path must identify a file inside the benchmark package")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    algorithm = manifest.get("hash_algorithm", manifest.get("algorithm"))
    if algorithm not in {"SHA-256", "sha256"}:
        raise ValueError("Unsupported hash algorithm in manifest")
    if manifest.get("hash_normalization") != NORMALIZATION:
        raise ValueError("Manifest does not declare the supported line-ending normalization")
    entries = manifest_entries(manifest.get("files"))
    if not entries:
        raise ValueError("Manifest has no file digests")

    checked = 0
    for relative, expected in entries:
        candidate = (HERE / relative).resolve()
        if candidate == manifest_path or HERE not in candidate.parents:
            raise ValueError(f"Manifest path is outside the package or hashes itself: {relative!r}")
        if not candidate.is_file():
            raise ValueError(f"Manifest file is missing: {relative}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Manifest digest is not a lowercase SHA-256 value: {relative}")
        actual = hashlib.sha256(normalized_bytes(candidate)).hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {relative}: expected {expected}, got {actual}")
        checked += 1
    print(f"Verified {checked} files in {manifest_path.name} using normalized-text SHA-256.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("sha256-manifest.json"))
    args = parser.parse_args()
    try:
        return verify(args.manifest)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"SHA-256 verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
