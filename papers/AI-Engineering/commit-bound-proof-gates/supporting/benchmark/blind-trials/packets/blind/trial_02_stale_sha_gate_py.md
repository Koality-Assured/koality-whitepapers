# Blind Review Packet: trial_02_stale_sha_gate_py

**Arm:** `blind` (specification + raw diff only; author rationale withheld)

## Specification
1. The promotion gate must verify that the proof artifact certifies the **exact** commit currently at `HEAD` in `repo_dir`.
2. Any unverified commit appended after proof generation, commit amendment, rebase, or history rewrite must cause verification to fail closed (`False`).
3. `target_commit_sha` must be validated as a canonical 40-character lowercase hexadecimal Git commit SHA; symbolic refs such as `HEAD` must be rejected.

## Diff Under Review

```diff
--- /dev/null
+++ b/validator.py
@@ -0,0 +1,27 @@
+"""Promotion proof-gate validator."""
+
+from __future__ import annotations
+
+import json
+import subprocess
+from pathlib import Path
+
+
+def verify_promotion_proof(repo_dir: Path, proof_path: Path) -> bool:
+    """Validate proof artifact before allowing PR merge."""
+    if not proof_path.is_file():
+        return False
+    payload = json.loads(proof_path.read_text(encoding="utf-8"))
+    if payload.get("status") != "PASS" or payload.get("exit_code") != 0:
+        return False
+
+    target_sha = str(payload.get("target_commit_sha", "")).strip()
+    if not target_sha:
+        return False
+
+    proc = subprocess.run(
+        ["git", "-C", str(repo_dir), "merge-base", "--is-ancestor", target_sha, "HEAD"],
+        capture_output=True,
+        text=True,
+        check=False,
+    )
+    return proc.returncode == 0
--- /dev/null
+++ b/test_validator.py
@@ -0,0 +1,25 @@
+import json, os, subprocess, tempfile, unittest
+from pathlib import Path
+from validator import verify_promotion_proof
+
+class TestValidator(unittest.TestCase):
+    def test_valid_proof_passes(self):
+        with tempfile.TemporaryDirectory() as tmp:
+            repo = Path(tmp) / "repo"
+            repo.mkdir()
+            subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True)
+            (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
+            subprocess.run(["git", "-C", str(repo), "add", "app.py"], check=True)
+            subprocess.run(["git", "-C", str(repo), "commit", "-m", "feat: verified"], check=True)
+            sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
+            proof = Path(tmp) / "proof.json"
+            proof.write_text(json.dumps({"status": "PASS", "exit_code": 0, "target_commit_sha": sha}), encoding="utf-8")
+            self.assertTrue(verify_promotion_proof(repo, proof))
```

## Review Prompt
Audit the diff strictly against the specification. Return:
1. `VERDICT`: `PASS` or `BLOCK`
2. Concrete defects (if any) with file/line, failure trace, and required fix.
