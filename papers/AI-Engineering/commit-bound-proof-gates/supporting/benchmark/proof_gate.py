#!/usr/bin/env python3
"""Commit-bound proof gate verification and negative-routing tier classifier.

Implements fail-closed verification primitives grounded in the Agent Factory
promotion contract:
  1. Naive status-only baseline (status/exit_code only).
  2. Ancestry-only gate (git merge-base --is-ancestor without exact HEAD match).
  3. Strict commit-bound gate (exact HEAD == target_commit_sha, Git ancestry,
     detached-HEAD and dirty-worktree checks, independent reviewer attestation,
     cross-model diversity, and negative-routing verification).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

CANONICAL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_PROOF_MODES = frozenset({"local-replay", "staging"})
VALID_TIERS = frozenset({"direct", "full-assurance"})

REQUIRED_CORE_FIELDS = (
    "run_id",
    "target_commit_sha",
    "status",
    "proof_mode",
    "replay_command",
    "exit_code",
    "verified_at",
)

REQUIRED_ATTESTATION_FIELDS = (
    "author_id",
    "reviewer_id",
    "author_model_family",
    "reviewer_model_family",
    "tier",
    "negative_route_checked",
)

ALLOWED_PROOF_FIELDS = frozenset(
    (*REQUIRED_CORE_FIELDS, *REQUIRED_ATTESTATION_FIELDS, "staging_host")
)

# Boundary triggers that force full-assurance regardless of file count.
_CAMEL_BOUNDARY_1_RE = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_BOUNDARY_2_RE = re.compile(r"([A-Z]+)([A-Z][a-z])")

_SECURITY_BOUNDARY_RE = re.compile(
    r"\b(auth|jwt|oauth|token|session|acl|rbac|permission|privilege|"
    r"sanitize|traversal|secret|crypt|hmac|signature|verify proof)\b",
    re.IGNORECASE,
)
_CONCURRENCY_BOUNDARY_RE = re.compile(
    r"\b(mutex|rwmutex|lock|unlock|lease|goroutine|atomic|race|semaphore|"
    r"asyncio\.lock|threading\.lock|compare and swap)\b",
    re.IGNORECASE,
)
_PUBLIC_API_OR_SCHEMA_RE = re.compile(
    r"\b(schema|openapi|endpoint|router\.|app\.(get|post|put|delete|patch)|"
    r"http\.handlefunc|export\s+(async\s+)?function)\b",
    re.IGNORECASE,
)


def _normalize_identifiers(text: str) -> str:
    """Split CamelCase and snake_case identifiers into space-separated sub-tokens."""
    step1 = _CAMEL_BOUNDARY_1_RE.sub(r"\1 \2", text)
    step2 = _CAMEL_BOUNDARY_2_RE.sub(r"\1 \2", step1)
    return step2.replace("_", " ")
_SEMVER_BUMP_RE = re.compile(
    r'^[+-]\s*"?[a-zA-Z0-9_@./-]+"?\s*(?::|=|>=|<=|==|~=|v|\s)\s*"?[\^~>=<]*v?\d+\.\d+\.\d+"?,?\s*$'
)
_MANIFEST_FILENAMES = frozenset(
    {"package.json", "package-lock.json", "pyproject.toml", "go.mod", "requirements.txt"}
)
_DOC_SUFFIXES = frozenset({".md", ".txt", ".rst"})


@dataclass(frozen=True)
class GateResult:
    """Structured fail-closed gate verdict."""

    passed: bool
    gate_mode: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    observed_head_sha: str | None = None
    observed_branch: str | None = None
    is_detached_head: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "gate_mode": self.gate_mode,
            "reasons": list(self.reasons),
            "observed_head_sha": self.observed_head_sha,
            "observed_branch": self.observed_branch,
            "is_detached_head": self.is_detached_head,
        }


@dataclass(frozen=True)
class RoutingDecision:
    """Result of deterministic execution-tier classification."""

    tier: str
    classifier: str
    reasons: tuple[str, ...]
    negative_route_checked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "classifier": self.classifier,
            "reasons": list(self.reasons),
            "negative_route_checked": self.negative_route_checked,
        }


def _run_git(repo_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _load_proof_json(proof_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not proof_path.is_file():
        return None, f"missing proof artifact: {proof_path.name}"
    try:
        raw = proof_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"corrupt proof artifact: {exc}"
    if not isinstance(payload, dict):
        return None, "proof payload must be a JSON object"
    return payload, None


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_iso8601_utc(value: Any) -> bool:
    if not _is_nonempty_str(value):
        return False
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_core_proof_fields(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key in REQUIRED_CORE_FIELDS:
        if key not in payload:
            reasons.append(f"missing required field: {key}")

    if "run_id" in payload and not _is_nonempty_str(payload["run_id"]):
        reasons.append("run_id must be a non-empty string")

    sha = payload.get("target_commit_sha")
    if "target_commit_sha" in payload:
        if not isinstance(sha, str) or not CANONICAL_SHA_RE.fullmatch(sha):
            reasons.append("target_commit_sha must be a canonical 40-char lowercase hex SHA")

    if payload.get("status") != "PASS":
        reasons.append(f"status must be 'PASS', got {payload.get('status')!r}")

    exit_code = payload.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
        reasons.append(f"exit_code must be integer 0, got {exit_code!r}")

    proof_mode = payload.get("proof_mode")
    if proof_mode not in VALID_PROOF_MODES:
        reasons.append(f"proof_mode must be one of {sorted(VALID_PROOF_MODES)}, got {proof_mode!r}")
    elif proof_mode == "staging" and not _is_nonempty_str(payload.get("staging_host")):
        reasons.append("staging_host is required when proof_mode is 'staging'")
    if "staging_host" in payload and not _is_nonempty_str(payload["staging_host"]):
        reasons.append("staging_host must be a non-empty string when present")

    if "replay_command" in payload and not _is_nonempty_str(payload["replay_command"]):
        reasons.append("replay_command must be a non-empty string")

    if "verified_at" in payload and not _is_valid_iso8601_utc(payload["verified_at"]):
        reasons.append("verified_at must be a timezone-aware ISO-8601 timestamp")

    return reasons


def _inspect_git_head(repo_dir: Path) -> tuple[str | None, str | None, bool, list[str]]:
    reasons: list[str] = []
    head_proc = _run_git(repo_dir, ["rev-parse", "--verify", "HEAD"])
    if head_proc.returncode != 0:
        reasons.append("failed to resolve HEAD in target repository")
        return None, None, True, reasons
    head_sha = head_proc.stdout.strip()
    if not CANONICAL_SHA_RE.fullmatch(head_sha):
        reasons.append(f"unexpected HEAD SHA format: {head_sha!r}")
        return None, None, True, reasons

    sym_proc = _run_git(repo_dir, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if sym_proc.returncode == 0:
        branch_name = sym_proc.stdout.strip()
        is_detached = False
    else:
        branch_name = None
        is_detached = True
    return head_sha, branch_name, is_detached, reasons


def verify_naive_status_only(proof_path: Path) -> GateResult:
    """Arm 1 baseline: trusts PASS status and exit_code 0 without Git binding."""
    payload, load_err = _load_proof_json(proof_path)
    if load_err or payload is None:
        return GateResult(passed=False, gate_mode="naive_status_only", reasons=(load_err or "load error",))

    reasons: list[str] = []
    if payload.get("status") != "PASS":
        reasons.append(f"status must be 'PASS', got {payload.get('status')!r}")
    exit_code = payload.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
        reasons.append(f"exit_code must be integer 0, got {exit_code!r}")
    return GateResult(passed=not reasons, gate_mode="naive_status_only", reasons=tuple(reasons))


def verify_ancestry_only(repo_dir: Path, proof_path: Path) -> GateResult:
    """Arm 2 baseline: validates core fields and git merge-base --is-ancestor only."""
    payload, load_err = _load_proof_json(proof_path)
    if load_err or payload is None:
        return GateResult(passed=False, gate_mode="ancestry_only", reasons=(load_err or "load error",))

    reasons = _validate_core_proof_fields(payload)
    head_sha, branch_name, is_detached, git_errs = _inspect_git_head(repo_dir)
    reasons.extend(git_errs)

    sha = payload.get("target_commit_sha")
    if isinstance(sha, str) and CANONICAL_SHA_RE.fullmatch(sha) and head_sha:
        obj_proc = _run_git(repo_dir, ["cat-file", "-t", sha])
        if obj_proc.returncode != 0 or obj_proc.stdout.strip() != "commit":
            reasons.append(f"target_commit_sha {sha[:12]} is not a commit object in repository")
        else:
            anc_proc = _run_git(repo_dir, ["merge-base", "--is-ancestor", sha, head_sha])
            if anc_proc.returncode != 0:
                reasons.append(
                    f"target_commit_sha {sha[:12]} is not an ancestor of HEAD {head_sha[:12]}"
                )

    return GateResult(
        passed=not reasons,
        gate_mode="ancestry_only",
        reasons=tuple(reasons),
        observed_head_sha=head_sha,
        observed_branch=branch_name,
        is_detached_head=is_detached,
    )


def verify_strict_commit_bound(
    repo_dir: Path,
    proof_path: Path,
    *,
    expected_branch: str | None = None,
    require_clean_worktree: bool = True,
    require_cross_model: bool = True,
) -> GateResult:
    """Arm 3 strict gate: exact HEAD binding, ancestry, attestation, and hygiene."""
    payload, load_err = _load_proof_json(proof_path)
    if load_err or payload is None:
        return GateResult(passed=False, gate_mode="strict_commit_bound", reasons=(load_err or "load error",))

    reasons = _validate_core_proof_fields(payload)

    extra_fields = sorted(set(payload) - ALLOWED_PROOF_FIELDS)
    if extra_fields:
        reasons.append(f"unexpected proof fields prohibited: {', '.join(extra_fields)}")

    # Attestation, cross-model diversity, and negative routing invariants
    for key in REQUIRED_ATTESTATION_FIELDS:
        if key not in payload:
            reasons.append(f"missing attestation/routing field: {key}")

    author_id = payload.get("author_id")
    reviewer_id = payload.get("reviewer_id")
    if "author_id" in payload and not _is_nonempty_str(author_id):
        reasons.append("author_id must be a non-empty string")
    if "reviewer_id" in payload and not _is_nonempty_str(reviewer_id):
        reasons.append("reviewer_id must be a non-empty string")
    if _is_nonempty_str(author_id) and _is_nonempty_str(reviewer_id):
        if str(author_id).strip().lower() == str(reviewer_id).strip().lower():
            reasons.append("author_id and reviewer_id must be distinct (self-attestation prohibited)")

    author_family = payload.get("author_model_family")
    reviewer_family = payload.get("reviewer_model_family")
    if "author_model_family" in payload and not _is_nonempty_str(author_family):
        reasons.append("author_model_family must be a non-empty string")
    if "reviewer_model_family" in payload and not _is_nonempty_str(reviewer_family):
        reasons.append("reviewer_model_family must be a non-empty string")
    if require_cross_model and _is_nonempty_str(author_family) and _is_nonempty_str(reviewer_family):
        if str(author_family).strip().lower() == str(reviewer_family).strip().lower():
            reasons.append("cross-model diversity violated: author and reviewer share model family")

    tier = payload.get("tier")
    if "tier" in payload and tier not in VALID_TIERS:
        reasons.append(f"tier must be one of {sorted(VALID_TIERS)}, got {tier!r}")
    if payload.get("negative_route_checked") is not True:
        reasons.append("negative_route_checked must be boolean true")

    # Git repository checks
    head_sha, branch_name, is_detached, git_errs = _inspect_git_head(repo_dir)
    reasons.extend(git_errs)

    if expected_branch is not None:
        if is_detached:
            reasons.append(f"detached HEAD mismatch: expected branch {expected_branch!r}")
        elif branch_name != expected_branch:
            reasons.append(f"branch mismatch: expected {expected_branch!r}, got {branch_name!r}")

    sha = payload.get("target_commit_sha")
    if isinstance(sha, str) and CANONICAL_SHA_RE.fullmatch(sha) and head_sha:
        obj_proc = _run_git(repo_dir, ["cat-file", "-t", sha])
        if obj_proc.returncode != 0 or obj_proc.stdout.strip() != "commit":
            reasons.append(f"target_commit_sha {sha[:12]} is not a commit object in repository")
        else:
            anc_proc = _run_git(repo_dir, ["merge-base", "--is-ancestor", sha, head_sha])
            if anc_proc.returncode != 0:
                reasons.append(
                    f"target_commit_sha {sha[:12]} is not an ancestor of HEAD {head_sha[:12]}"
                )
            if head_sha != sha:
                reasons.append(
                    f"HEAD commit mismatch: proof bound to {sha[:12]}, current HEAD is {head_sha[:12]}"
                )

    if require_clean_worktree:
        status_proc = _run_git(repo_dir, ["status", "--porcelain", "--untracked-files=no"])
        if status_proc.returncode != 0:
            reasons.append("failed to inspect worktree status")
        elif status_proc.stdout.strip():
            reasons.append("dirty tracked worktree detected after verification")

    return GateResult(
        passed=not reasons,
        gate_mode="strict_commit_bound",
        reasons=tuple(reasons),
        observed_head_sha=head_sha,
        observed_branch=branch_name,
        is_detached_head=is_detached,
    )


def _is_doc_file(path_str: str) -> bool:
    return Path(path_str).suffix.lower() in _DOC_SUFFIXES


def _is_test_file(path_str: str) -> bool:
    lower = path_str.lower()
    name = Path(lower).name
    return (
        "/tests/" in lower
        or "\\tests\\" in lower
        or lower.startswith("tests/")
        or name.startswith("test_")
        or name.endswith("_test.go")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
    )


def _is_semver_only_manifest_diff(changed_files: list[str], diff_text: str) -> bool:
    if not changed_files:
        return False
    if not all(Path(f).name in _MANIFEST_FILENAMES for f in changed_files):
        return False
    added_or_removed = [
        line
        for line in diff_text.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    if not added_or_removed:
        return False
    return all(_SEMVER_BUMP_RE.match(line.strip()) for line in added_or_removed)


def classify_execution_tier(
    changed_files: list[str],
    diff_text: str,
    *,
    has_regression_test: bool = False,
    classifier: str = "deterministic_boundary",
) -> RoutingDecision:
    """Classify a synthetic change into 'direct' vs 'full-assurance'."""
    if classifier == "always_full_assurance":
        return RoutingDecision(
            tier="full-assurance",
            classifier=classifier,
            reasons=("coordinator defaults every change to full-assurance",),
            negative_route_checked=False,
        )

    if classifier == "naive_file_count":
        tier = "direct" if len(changed_files) <= 1 else "full-assurance"
        return RoutingDecision(
            tier=tier,
            classifier=classifier,
            reasons=(f"changed_file_count={len(changed_files)}",),
            negative_route_checked=False,
        )

    if classifier != "deterministic_boundary":
        raise ValueError(f"Unsupported classifier: {classifier!r}")

    if not changed_files:
        return RoutingDecision(
            tier="full-assurance",
            classifier=classifier,
            reasons=("empty changed_files fails closed to full-assurance",),
        )

    # 1. Pure documentation / markdown / prose edits -> direct
    if all(_is_doc_file(path) for path in changed_files):
        return RoutingDecision(
            tier="direct",
            classifier=classifier,
            reasons=("pure documentation/markdown change touches no runtime or security boundary",),
        )

    # 2. Semver-only dependency updates -> direct
    if _is_semver_only_manifest_diff(changed_files, diff_text):
        return RoutingDecision(
            tier="direct",
            classifier=classifier,
            reasons=("semver-bounded dependency version bump only",),
        )

    # 3. Inspect diff content and paths for high-risk boundaries
    normalized_diff = _normalize_identifiers(diff_text)
    normalized_paths = [_normalize_identifiers(p) for p in changed_files]
    reasons: list[str] = []
    if (
        _SECURITY_BOUNDARY_RE.search(diff_text)
        or _SECURITY_BOUNDARY_RE.search(normalized_diff)
        or any(_SECURITY_BOUNDARY_RE.search(p) for p in normalized_paths)
    ):
        reasons.append("touches authentication, authorization, secret, or proof-verification boundary")
    if _CONCURRENCY_BOUNDARY_RE.search(diff_text) or _CONCURRENCY_BOUNDARY_RE.search(normalized_diff):
        reasons.append("touches concurrency, lock, lease, or synchronization primitive")
    if (
        _PUBLIC_API_OR_SCHEMA_RE.search(diff_text)
        or _PUBLIC_API_OR_SCHEMA_RE.search(normalized_diff)
        or any("schema" in p.lower() for p in changed_files)
    ):
        reasons.append("adds or modifies public API route, signature, or schema contract")

    non_test_files = [path for path in changed_files if not _is_test_file(path)]
    top_modules = {Path(path).parts[0] if len(Path(path).parts) > 1 else Path(path).name for path in non_test_files}
    if len(non_test_files) > 2 or len(top_modules) > 1:
        reasons.append("cross-module or multi-file production refactor requires full-assurance")

    if reasons:
        return RoutingDecision(tier="full-assurance", classifier=classifier, reasons=tuple(reasons))

    # 4. Scoped single-module change (with optional coupled test file) -> direct
    if len(non_test_files) <= 1 and (has_regression_test or any(_is_test_file(p) for p in changed_files)):
        return RoutingDecision(
            tier="direct",
            classifier=classifier,
            reasons=("scoped single-module fix backed by regression test",),
        )

    if len(non_test_files) == 1:
        return RoutingDecision(
            tier="direct",
            classifier=classifier,
            reasons=("scoped single-module refactor without public API, auth, or concurrency edges",),
        )

    return RoutingDecision(
        tier="full-assurance",
        classifier=classifier,
        reasons=("unclassified multi-file change fails safe to full-assurance",),
    )
