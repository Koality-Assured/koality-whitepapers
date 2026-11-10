"""Unit and adversarial reproduction tests for trial_02_stale_sha_gate_py."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from validator import verify_promotion_proof

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Synthetic",
    "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
    "GIT_COMMITTER_NAME": "Synthetic",
    "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
}


def _git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        env=GIT_ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


class TestStaleShaGate(unittest.TestCase):
    def test_valid_proof_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, ["init", "-b", "main"])
            (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
            _git(repo, ["add", "app.py"])
            _git(repo, ["commit", "-m", "feat: verified"])
            sha = _git(repo, ["rev-parse", "HEAD"])
            proof = Path(tmp) / "proof.json"
            proof.write_text(
                json.dumps({"status": "PASS", "exit_code": 0, "target_commit_sha": sha}),
                encoding="utf-8",
            )
            self.assertTrue(verify_promotion_proof(repo, proof))

    def test_repro_trailing_unverified_commit_bypasses_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, ["init", "-b", "main"])
            (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
            _git(repo, ["add", "app.py"])
            _git(repo, ["commit", "-m", "feat: verified"])
            verified_sha = _git(repo, ["rev-parse", "HEAD"])

            proof = Path(tmp) / "proof.json"
            proof.write_text(
                json.dumps({"status": "PASS", "exit_code": 0, "target_commit_sha": verified_sha}),
                encoding="utf-8",
            )

            # Unverified trailing commit pushed after proof generation
            (repo / "app.py").write_text("x = 999  # unverified\n", encoding="utf-8")
            _git(repo, ["add", "app.py"])
            _git(repo, ["commit", "-m", "fix: unverified post-proof edit"])

            # Expected secure contract: must return False
            self.assertFalse(verify_promotion_proof(repo, proof))
