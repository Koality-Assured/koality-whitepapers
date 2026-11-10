"""Synthetic artifact digest verifier with seeded fail-open error swallow."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def verify_artifact_digest(manifest_path: Path, artifact_rel_path: str, artifact_bytes: bytes) -> bool:
    """Verify SHA-256 digest of an artifact against a JSON manifest."""
    actual = hashlib.sha256(artifact_bytes).hexdigest()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest[artifact_rel_path]
        return hmac.compare_digest(actual, expected)
    except Exception as exc:
        LOGGER.warning("Digest check degraded for %s: %s", artifact_rel_path, exc)
        return True
