#!/usr/bin/env python3
"""Ephemeral multi-language synthetic Git repositories and routing diff fixtures."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

VERIFIED_TIMESTAMP = "2026-11-10T14:00:00Z"

_GIT_ENV_OVERRIDES = {
    "GIT_AUTHOR_NAME": "Synthetic Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_AUTHOR_DATE": "2026-11-10T14:00:00Z",
    "GIT_COMMITTER_NAME": "Synthetic Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    "GIT_COMMITTER_DATE": "2026-11-10T14:00:00Z",
}

_LANGUAGE_TEMPLATES: dict[str, dict[str, str]] = {
    "python": {
        "source_path": "src/validator.py",
        "test_path": "tests/test_validator.py",
        "replay_command": "python -m unittest tests/test_validator.py",
        "base_source": (
            "def validate_limit(value: int) -> bool:\n"
            "    return value >= 0\n"
        ),
        "fix_source": (
            "def validate_limit(value: int) -> bool:\n"
            "    return 0 <= value <= 100\n"
        ),
        "amend_source": (
            "def validate_limit(value: int) -> bool:\n"
            "    return 0 <= value <= 999\n"
        ),
        "trailing_source": (
            "def validate_limit(value: int) -> bool:\n"
            "    return True  # unverified post-proof bypass\n"
        ),
        "base_test": (
            "import unittest\n"
            "from src.validator import validate_limit\n\n"
            "class TestValidator(unittest.TestCase):\n"
            "    def test_bounds(self):\n"
            "        self.assertTrue(validate_limit(50))\n"
            "        self.assertFalse(validate_limit(101))\n"
        ),
    },
    "go": {
        "source_path": "pkg/limiter/limiter.go",
        "test_path": "pkg/limiter/limiter_test.go",
        "replay_command": "go test ./pkg/limiter/...",
        "base_source": (
            "package limiter\n\n"
            "func ValidLimit(v int) bool {\n"
            "\treturn v >= 0\n"
            "}\n"
        ),
        "fix_source": (
            "package limiter\n\n"
            "func ValidLimit(v int) bool {\n"
            "\treturn v >= 0 && v <= 100\n"
            "}\n"
        ),
        "amend_source": (
            "package limiter\n\n"
            "func ValidLimit(v int) bool {\n"
            "\treturn v >= 0 && v <= 999\n"
            "}\n"
        ),
        "trailing_source": (
            "package limiter\n\n"
            "func ValidLimit(v int) bool {\n"
            "\treturn true // unverified post-proof bypass\n"
            "}\n"
        ),
        "base_test": (
            "package limiter\n\n"
            "import \"testing\"\n\n"
            "func TestValidLimit(t *testing.T) {\n"
            "\tif !ValidLimit(50) || ValidLimit(101) {\n"
            "\t\tt.Fatal(\"bounds check failed\")\n"
            "\t}\n"
            "}\n"
        ),
    },
    "javascript": {
        "source_path": "src/limiter.js",
        "test_path": "tests/limiter.test.js",
        "replay_command": "node --test tests/limiter.test.js",
        "base_source": (
            "export function validLimit(value) {\n"
            "  return Number.isInteger(value) && value >= 0;\n"
            "}\n"
        ),
        "fix_source": (
            "export function validLimit(value) {\n"
            "  return Number.isInteger(value) && value >= 0 && value <= 100;\n"
            "}\n"
        ),
        "amend_source": (
            "export function validLimit(value) {\n"
            "  return Number.isInteger(value) && value >= 0 && value <= 999;\n"
            "}\n"
        ),
        "trailing_source": (
            "export function validLimit(_value) {\n"
            "  return true; // unverified post-proof bypass\n"
            "}\n"
        ),
        "base_test": (
            "import test from 'node:test';\n"
            "import assert from 'node:assert/strict';\n"
            "import { validLimit } from '../src/limiter.js';\n\n"
            "test('validLimit enforces bounds', () => {\n"
            "  assert.equal(validLimit(50), true);\n"
            "  assert.equal(validLimit(101), false);\n"
            "});\n"
        ),
    },
}


@dataclass(frozen=True)
class RepoFixtureContext:
    """Prepared ephemeral repository and proof artifact context."""

    repo_dir: Path
    proof_path: Path
    expected_branch: str | None
    expected_strict_pass: bool
    expected_ancestry_pass: bool
    category: str
    language: str
    scenario_id: str
    description: str


@dataclass(frozen=True)
class RoutingSample:
    """Labeled synthetic diff sample for tier classification evaluation."""

    sample_id: str
    language: str
    expected_tier: str
    changed_files: list[str]
    diff_text: str
    has_regression_test: bool
    rationale: str


def _git(repo_dir: Path, args: list[str], step_seconds: int = 0) -> str:
    env = os.environ.copy()
    env.update(_GIT_ENV_OVERRIDES)
    if step_seconds:
        ts = f"2026-11-10T14:00:{step_seconds:02d}Z"
        env["GIT_AUTHOR_DATE"] = ts
        env["GIT_COMMITTER_DATE"] = ts
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.strip()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _init_base_repo(repo_dir: Path, language: str) -> tuple[str, str]:
    tpl = _LANGUAGE_TEMPLATES[language]
    _git(repo_dir, ["init", "-b", "main"])
    _git(repo_dir, ["config", "user.name", "Synthetic Author"])
    _git(repo_dir, ["config", "user.email", "author@example.invalid"])
    _write_text(repo_dir / tpl["source_path"], tpl["base_source"])
    _write_text(repo_dir / tpl["test_path"], tpl["base_test"])
    _write_text(repo_dir / "README.md", "# Synthetic Multi-Language Fixture\n")
    _git(repo_dir, ["add", "."])
    _git(repo_dir, ["commit", "-m", "chore: initial baseline"], step_seconds=1)
    base_sha = _git(repo_dir, ["rev-parse", "HEAD"])

    _git(repo_dir, ["checkout", "-b", "feat/bound-fix"])
    _write_text(repo_dir / tpl["source_path"], tpl["fix_source"])
    _git(repo_dir, ["add", tpl["source_path"]])
    _git(
        repo_dir,
        [
            "commit",
            "-m",
            "fix: enforce upper limit bound\n\n"
            "Co-Authored-By: Agent Factory <agent-factory@local>\n"
            "X-Factory-Run: run-001\n"
            "X-Factory-Ledger-ID: run-001-f-01",
        ],
        step_seconds=2,
    )
    fix_sha = _git(repo_dir, ["rev-parse", "HEAD"])
    return base_sha, fix_sha


def _default_proof_payload(language: str, target_sha: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": "run-001",
        "target_commit_sha": target_sha,
        "status": "PASS",
        "proof_mode": "local-replay",
        "replay_command": _LANGUAGE_TEMPLATES[language]["replay_command"],
        "exit_code": 0,
        "verified_at": VERIFIED_TIMESTAMP,
        "author_id": "leo",
        "reviewer_id": "nadia",
        "author_model_family": "gemini",
        "reviewer_model_family": "claude",
        "tier": "direct",
        "negative_route_checked": True,
    }
    payload.update(overrides)
    return payload


def _write_proof(proof_path: Path, payload: dict[str, Any]) -> None:
    _write_text(proof_path, json.dumps(payload, indent=2) + "\n")


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    category: str
    language: str
    expected_strict_pass: bool
    expected_ancestry_pass: bool
    description: str
    builder: Callable[[Path, Path], str | None]


def _build_clean(repo_dir: Path, proof_path: Path, language: str, **proof_overrides: Any) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha, **proof_overrides))
    return "feat/bound-fix"


def _build_amend(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    tpl = _LANGUAGE_TEMPLATES[language]
    _write_text(repo_dir / tpl["source_path"], tpl["amend_source"])
    _git(repo_dir, ["add", tpl["source_path"]])
    _git(repo_dir, ["commit", "--amend", "--no-edit"], step_seconds=5)
    return "feat/bound-fix"


def _build_rebase(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    _git(repo_dir, ["checkout", "main"])
    _write_text(repo_dir / "CHANGELOG.md", "## Unreleased\n- Upstream maintenance\n")
    _git(repo_dir, ["add", "CHANGELOG.md"])
    _git(repo_dir, ["commit", "-m", "docs: advance main"], step_seconds=6)
    _git(repo_dir, ["checkout", "feat/bound-fix"])
    _git(repo_dir, ["rebase", "main"], step_seconds=7)
    return "feat/bound-fix"


def _build_cherry_pick(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    _git(repo_dir, ["checkout", "-b", "release/v1", "main"])
    _write_text(repo_dir / "RELEASE.txt", "release/v1\n")
    _git(repo_dir, ["add", "RELEASE.txt"])
    _git(repo_dir, ["commit", "-m", "chore: prep release branch"], step_seconds=8)
    _git(repo_dir, ["cherry-pick", fix_sha], step_seconds=9)
    return "release/v1"


def _build_trailing_commit(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    tpl = _LANGUAGE_TEMPLATES[language]
    _write_text(repo_dir / tpl["source_path"], tpl["trailing_source"])
    _git(repo_dir, ["add", tpl["source_path"]])
    _git(repo_dir, ["commit", "-m", "fix: unverified post-proof tweak"], step_seconds=10)
    return "feat/bound-fix"


def _build_forced_reset(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    _git(repo_dir, ["reset", "--hard", "HEAD~1"])
    tpl = _LANGUAGE_TEMPLATES[language]
    _write_text(repo_dir / tpl["source_path"], tpl["amend_source"])
    _git(repo_dir, ["add", tpl["source_path"]])
    _git(repo_dir, ["commit", "-m", "fix: rewritten history after reset"], step_seconds=11)
    return "feat/bound-fix"


def _build_detached_mismatch(repo_dir: Path, proof_path: Path, language: str) -> str:
    base_sha, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    _git(repo_dir, ["checkout", "--detach", base_sha])
    return "feat/bound-fix"


def _build_detached_same_sha(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    _git(repo_dir, ["checkout", "--detach", fix_sha])
    return "feat/bound-fix"


def _build_dirty_worktree(repo_dir: Path, proof_path: Path, language: str) -> str:
    _, fix_sha = _init_base_repo(repo_dir, language)
    _write_proof(proof_path, _default_proof_payload(language, fix_sha))
    tpl = _LANGUAGE_TEMPLATES[language]
    _write_text(repo_dir / tpl["source_path"], tpl["trailing_source"])
    return "feat/bound-fix"


def _build_raw_proof(
    repo_dir: Path, proof_path: Path, language: str, raw_content: str | None
) -> str:
    _init_base_repo(repo_dir, language)
    if raw_content is not None:
        _write_text(proof_path, raw_content)
    return "feat/bound-fix"


def get_proof_scenarios() -> list[ScenarioSpec]:
    """Return the complete adversarial Git and proof-tampering test matrix."""
    return [
        ScenarioSpec(
            "clean_commit_python",
            "clean_commit",
            "python",
            True,
            True,
            "Clean Python branch tip matching target_commit_sha and full attestations",
            lambda r, p: _build_clean(r, p, "python"),
        ),
        ScenarioSpec(
            "clean_commit_go",
            "clean_commit",
            "go",
            True,
            True,
            "Clean Go branch tip matching target_commit_sha and full attestations",
            lambda r, p: _build_clean(r, p, "go"),
        ),
        ScenarioSpec(
            "clean_commit_javascript_staging",
            "clean_commit",
            "javascript",
            True,
            True,
            "Clean JavaScript branch tip with staging mode and declared staging_host",
            lambda r, p: _build_clean(
                r,
                p,
                "javascript",
                proof_mode="staging",
                staging_host="https://staging.example.invalid",
            ),
        ),
        ScenarioSpec(
            "post_proof_amend_python",
            "amend",
            "python",
            False,
            False,
            "Post-proof git commit --amend alters SHA and invalidates proof",
            lambda r, p: _build_amend(r, p, "python"),
        ),
        ScenarioSpec(
            "post_proof_amend_go",
            "amend",
            "go",
            False,
            False,
            "Post-proof git commit --amend on Go branch alters SHA",
            lambda r, p: _build_amend(r, p, "go"),
        ),
        ScenarioSpec(
            "post_proof_rebase_python",
            "rebase",
            "python",
            False,
            False,
            "Post-proof git rebase onto updated main orphans target_commit_sha",
            lambda r, p: _build_rebase(r, p, "python"),
        ),
        ScenarioSpec(
            "post_proof_rebase_javascript",
            "rebase",
            "javascript",
            False,
            False,
            "Post-proof git rebase on JS branch orphans target_commit_sha",
            lambda r, p: _build_rebase(r, p, "javascript"),
        ),
        ScenarioSpec(
            "post_proof_cherry_pick_go",
            "cherry_pick",
            "go",
            False,
            False,
            "Post-proof git cherry-pick onto release/v1 creates new SHA",
            lambda r, p: _build_cherry_pick(r, p, "go"),
        ),
        ScenarioSpec(
            "post_proof_cherry_pick_python",
            "cherry_pick",
            "python",
            False,
            False,
            "Post-proof git cherry-pick onto release/v1 creates new SHA",
            lambda r, p: _build_cherry_pick(r, p, "python"),
        ),
        ScenarioSpec(
            "unverified_trailing_commit_python",
            "trailing_commit",
            "python",
            False,
            True,
            "Unverified commit added after proof; target_commit_sha remains ancestor of HEAD",
            lambda r, p: _build_trailing_commit(r, p, "python"),
        ),
        ScenarioSpec(
            "unverified_trailing_commit_go",
            "trailing_commit",
            "go",
            False,
            True,
            "Unverified Go commit added after proof; ancestry-only gate passes erroneously",
            lambda r, p: _build_trailing_commit(r, p, "go"),
        ),
        ScenarioSpec(
            "unverified_trailing_commit_javascript",
            "trailing_commit",
            "javascript",
            False,
            True,
            "Unverified JS commit added after proof; ancestry-only gate passes erroneously",
            lambda r, p: _build_trailing_commit(r, p, "javascript"),
        ),
        ScenarioSpec(
            "forced_reset_history_rewrite_python",
            "reset_and_detached",
            "python",
            False,
            False,
            "Forced git reset --hard HEAD~1 and rewritten commit invalidates proof",
            lambda r, p: _build_forced_reset(r, p, "python"),
        ),
        ScenarioSpec(
            "detached_head_mismatch_python",
            "reset_and_detached",
            "python",
            False,
            False,
            "Detached HEAD checked out at base commit diverges from branch proof",
            lambda r, p: _build_detached_mismatch(r, p, "python"),
        ),
        ScenarioSpec(
            "detached_head_same_sha_branch_mismatch",
            "reset_and_detached",
            "go",
            False,
            True,
            "Detached HEAD at target SHA when branch checkout is expected fails strict branch binding",
            lambda r, p: _build_detached_same_sha(r, p, "go"),
        ),
        ScenarioSpec(
            "dirty_worktree_post_proof_javascript",
            "reset_and_detached",
            "javascript",
            False,
            True,
            "Tracked source file modified after proof emitted without commit",
            lambda r, p: _build_dirty_worktree(r, p, "javascript"),
        ),
        ScenarioSpec(
            "missing_proof_file",
            "tampered_proof",
            "python",
            False,
            False,
            "Missing proof.json fails closed",
            lambda r, p: _build_raw_proof(r, p, "python", None),
        ),
        ScenarioSpec(
            "corrupt_json_proof",
            "tampered_proof",
            "python",
            False,
            False,
            "Malformed JSON proof.json fails closed",
            lambda r, p: _build_raw_proof(r, p, "python", "{bad json"),
        ),
        ScenarioSpec(
            "non_object_json_proof",
            "tampered_proof",
            "python",
            False,
            False,
            "Non-object JSON list fails closed",
            lambda r, p: _build_raw_proof(r, p, "python", "[]"),
        ),
        ScenarioSpec(
            "malformed_short_sha",
            "tampered_proof",
            "python",
            False,
            False,
            "Abbreviated 7-char SHA rejected",
            lambda r, p: _build_clean(r, p, "python", target_commit_sha="abcdef1"),
        ),
        ScenarioSpec(
            "malformed_symbolic_ref_sha",
            "tampered_proof",
            "python",
            False,
            False,
            "Symbolic ref 'HEAD' rejected as target_commit_sha",
            lambda r, p: _build_clean(r, p, "python", target_commit_sha="HEAD"),
        ),
        ScenarioSpec(
            "nonexistent_40hex_sha",
            "tampered_proof",
            "go",
            False,
            False,
            "Syntactically valid 40-hex SHA absent from Git ODB rejected",
            lambda r, p: _build_clean(r, p, "go", target_commit_sha="0" * 40),
        ),
        ScenarioSpec(
            "nonzero_exit_code_with_pass_status",
            "tampered_proof",
            "python",
            False,
            False,
            "Non-zero exit_code fails even when status is forged to PASS",
            lambda r, p: _build_clean(r, p, "python", exit_code=1, status="PASS"),
        ),
        ScenarioSpec(
            "boolean_exit_code_type_confusion",
            "tampered_proof",
            "python",
            False,
            False,
            "Boolean exit_code=false rejected despite bool subclassing int in Python",
            lambda r, p: _build_clean(r, p, "python", exit_code=False),
        ),
        ScenarioSpec(
            "fail_status_with_zero_exit",
            "tampered_proof",
            "javascript",
            False,
            False,
            "status='FAIL' with exit_code=0 fails closed",
            lambda r, p: _build_clean(r, p, "javascript", status="FAIL", exit_code=0),
        ),
        ScenarioSpec(
            "missing_replay_command",
            "tampered_proof",
            "python",
            False,
            False,
            "Empty replay_command fails closed",
            lambda r, p: _build_clean(r, p, "python", replay_command="   "),
        ),
        ScenarioSpec(
            "invalid_verified_at_timestamp",
            "tampered_proof",
            "python",
            False,
            False,
            "Invalid or naive verified_at timestamp fails closed",
            lambda r, p: _build_clean(r, p, "python", verified_at="2026-11-10"),
        ),
        ScenarioSpec(
            "staging_mode_missing_host",
            "tampered_proof",
            "python",
            False,
            False,
            "staging proof_mode without staging_host fails closed",
            lambda r, p: _build_clean(r, p, "python", proof_mode="staging"),
        ),
        ScenarioSpec(
            "self_signed_author_eq_reviewer",
            "tampered_proof",
            "python",
            False,
            True,
            "Author self-signing proof (author_id == reviewer_id) rejected by strict gate",
            lambda r, p: _build_clean(r, p, "python", author_id="leo", reviewer_id="leo"),
        ),
        ScenarioSpec(
            "same_model_family_violation",
            "tampered_proof",
            "go",
            False,
            True,
            "Author and reviewer sharing model family violates cross-model diversity",
            lambda r, p: _build_clean(
                r, p, "go", author_model_family="gemini", reviewer_model_family="gemini"
            ),
        ),
        ScenarioSpec(
            "missing_negative_route_check",
            "tampered_proof",
            "javascript",
            False,
            True,
            "negative_route_checked=false rejected by strict gate",
            lambda r, p: _build_clean(r, p, "javascript", negative_route_checked=False),
        ),
    ]


def materialize_scenario(spec: ScenarioSpec, work_root: Path) -> RepoFixtureContext:
    """Create an ephemeral synthetic Git repo and proof.json for a scenario."""
    repo_dir = work_root / spec.scenario_id / "repo"
    proof_dir = work_root / spec.scenario_id / "proof"
    repo_dir.mkdir(parents=True, exist_ok=True)
    proof_dir.mkdir(parents=True, exist_ok=True)
    proof_path = proof_dir / "proof.json"
    expected_branch = spec.builder(repo_dir, proof_path)
    return RepoFixtureContext(
        repo_dir=repo_dir,
        proof_path=proof_path,
        expected_branch=expected_branch,
        expected_strict_pass=spec.expected_strict_pass,
        expected_ancestry_pass=spec.expected_ancestry_pass,
        category=spec.category,
        language=spec.language,
        scenario_id=spec.scenario_id,
        description=spec.description,
    )


def get_routing_samples() -> list[RoutingSample]:
    """Return 16 labeled multi-language synthetic diffs for tier routing tests."""
    return [
        # 8 direct-tier cases per run-spec.md negative routing table
        RoutingSample(
            "direct_01_py_bugfix_with_test",
            "python",
            "direct",
            ["src/formatting.py", "tests/test_formatting.py"],
            "-    return text.strip()\n+    return text.strip().lower()\n",
            True,
            "Scoped bugfix in single Python module with regression test",
        ),
        RoutingSample(
            "direct_02_go_bugfix_with_test",
            "go",
            "direct",
            ["pkg/strings/trim.go", "pkg/strings/trim_test.go"],
            "- return strings.Trim(s, \" \")\n+ return strings.TrimSpace(s)\n",
            True,
            "Scoped bugfix in single Go package with unit test",
        ),
        RoutingSample(
            "direct_03_js_bugfix_with_test",
            "javascript",
            "direct",
            ["src/formatDate.js", "tests/formatDate.test.js"],
            "- return iso.slice(0, 9);\n+ return iso.slice(0, 10);\n",
            True,
            "Scoped bugfix in single JS helper with test coverage",
        ),
        RoutingSample(
            "direct_04_docs_markdown_typo",
            "markdown",
            "direct",
            ["docs/runbook.md", "docs/onboarding.md"],
            "- Run `pyton` before merge.\n+ Run `python` before merge.\n",
            False,
            "Pure markdown typo correction",
        ),
        RoutingSample(
            "direct_05_npm_semver_bump",
            "javascript",
            "direct",
            ["package.json"],
            '-    "htmlhint": "1.9.1",\n+    "htmlhint": "1.9.2",\n',
            False,
            "Standard patch dependency bump in package.json",
        ),
        RoutingSample(
            "direct_06_pyproject_semver_bump",
            "python",
            "direct",
            ["pyproject.toml"],
            '-  "jsonschema>=4.21.0",\n+  "jsonschema>=4.22.0",\n',
            False,
            "Standard minor dependency bump in pyproject.toml",
        ),
        RoutingSample(
            "direct_07_py_single_module_refactor",
            "python",
            "direct",
            ["src/metrics_summary.py"],
            "-    avg = total / count\n+    avg = round(total / count, 4)\n",
            False,
            "Scoped single-worktree calculation cleanup",
        ),
        RoutingSample(
            "direct_08_docs_txt_notes",
            "markdown",
            "direct",
            ["docs/CHANGELOG.md"],
            "+ Added release notes for v1.2.1.\n",
            False,
            "Documentation-only changelog entry",
        ),
        # 8 full-assurance cases
        RoutingSample(
            "full_01_py_auth_token_change",
            "python",
            "full-assurance",
            ["src/auth/jwt_guard.py"],
            "+ def verify_jwt_claims(token: str) -> dict:\n+     return decode(token, verify_exp=True)\n",
            True,
            "Single-file authentication boundary modification requires Nadia security gate",
        ),
        RoutingSample(
            "full_02_go_lease_mutex_change",
            "go",
            "full-assurance",
            ["pkg/coordinator/lease.go"],
            "+ func (m *Manager) AcquireLease(id string) bool {\n+     m.mu.Lock()\n",
            True,
            "Single-file concurrency/lease lock change requires full-assurance",
        ),
        RoutingSample(
            "full_03_js_path_traversal_sanitizer",
            "javascript",
            "full-assurance",
            ["src/export_sanitize.js"],
            "+ export function sanitizeExportPath(baseDir, relPath) {\n",
            True,
            "Path sanitization & security boundary modification",
        ),
        RoutingSample(
            "full_04_py_public_api_endpoint",
            "python",
            "full-assurance",
            ["src/routes.py"],
            "+ @app.post('/v1/tokens/rotate')\n+ def rotate_token():\n",
            True,
            "Adds new HTTP endpoint & touches token boundary",
        ),
        RoutingSample(
            "full_05_cross_module_architecture",
            "python",
            "full-assurance",
            ["ledger/store.py", "executor/runner.py", "promotion/pr.py"],
            "+ class LedgerDispatcher:\n+     pass\n",
            False,
            "Cross-module multi-file architectural change",
        ),
        RoutingSample(
            "full_06_schema_contract_change",
            "json",
            "full-assurance",
            ["docs/standards/proof.schema.json"],
            '+  "required": ["run_id", "target_commit_sha"]\n',
            False,
            "Schema contract change affects downstream gates",
        ),
        RoutingSample(
            "full_07_go_rbac_middleware",
            "go",
            "full-assurance",
            ["pkg/http/middleware.go", "pkg/http/middleware_test.go"],
            "+ func RequirePermission(role string) Handler {\n",
            True,
            "RBAC permission middleware requires Nadia security review",
        ),
        RoutingSample(
            "full_08_py_proof_gate_verifier",
            "python",
            "full-assurance",
            ["gates/verify_proof.py", "tests/test_verify_proof.py"],
            "+ def verify_proof_signature(proof_path, head_sha):\n",
            True,
            "Modifies proof verification gate boundary",
        ),
    ]
