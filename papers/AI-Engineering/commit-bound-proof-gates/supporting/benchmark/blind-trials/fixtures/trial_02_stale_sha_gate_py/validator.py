"""Synthetic proof-gate validator with seeded stale-SHA & ref-injection defects."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def verify_promotion_proof(repo_dir: Path, proof_path: Path) -> bool:
    """Validate proof artifact before allowing PR merge."""
    if not proof_path.is_file():
        return False
    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS" or payload.get("exit_code") != 0:
        return False

    target_sha = str(payload.get("target_commit_sha", "")).strip()
    if not target_sha:
        return False

    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "merge-base", "--is-ancestor", target_sha, "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0
