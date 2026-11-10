"""Unit and adversarial reproduction tests for trial_04_silent_error_swallow_py."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from receipt_check import verify_artifact_digest


class TestReceiptCheck(unittest.TestCase):
    def test_valid_digest_passes_and_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b"verified-content"
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"artifact.txt": hashlib.sha256(data).hexdigest()}),
                encoding="utf-8",
            )
            self.assertTrue(verify_artifact_digest(manifest, "artifact.txt", data))
            self.assertFalse(verify_artifact_digest(manifest, "artifact.txt", b"tampered"))

    def test_repro_corrupt_manifest_or_missing_entry_must_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corrupt_manifest = root / "manifest.json"
            corrupt_manifest.write_text("{corrupt", encoding="utf-8")

            # Expected secure contract: fail closed (False) on corrupt/missing manifest
            self.assertFalse(verify_artifact_digest(corrupt_manifest, "artifact.txt", b"tampered"))
            self.assertFalse(
                verify_artifact_digest(root / "absent.json", "artifact.txt", b"tampered")
            )
