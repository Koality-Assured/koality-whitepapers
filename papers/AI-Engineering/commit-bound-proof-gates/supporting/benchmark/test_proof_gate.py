#!/usr/bin/env python3
"""Unit tests for commit-bound proof gate and negative-routing tier classifier."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from proof_gate import (  # noqa: E402
    ALLOWED_PROOF_FIELDS,
    CANONICAL_SHA_RE,
    REQUIRED_ATTESTATION_FIELDS,
    REQUIRED_CORE_FIELDS,
    classify_execution_tier,
    verify_ancestry_only,
    verify_naive_status_only,
    verify_strict_commit_bound,
)
from synthetic_repos import (  # noqa: E402
    get_proof_scenarios,
    get_routing_samples,
    materialize_scenario,
)


class TestProofGateMatrix(unittest.TestCase):
    """Verify every positive, Git-mutation, and proof-tampering scenario."""

    def test_all_31_proof_scenarios(self) -> None:
        scenarios = get_proof_scenarios()
        self.assertEqual(len(scenarios), 31)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in scenarios:
                with self.subTest(scenario=spec.scenario_id):
                    ctx = materialize_scenario(spec, root)
                    strict_res = verify_strict_commit_bound(
                        ctx.repo_dir,
                        ctx.proof_path,
                        expected_branch=ctx.expected_branch,
                    )
                    ancestry_res = verify_ancestry_only(ctx.repo_dir, ctx.proof_path)

                    self.assertEqual(
                        strict_res.passed,
                        ctx.expected_strict_pass,
                        msg=f"{spec.scenario_id} strict={strict_res}",
                    )
                    self.assertEqual(
                        ancestry_res.passed,
                        ctx.expected_ancestry_pass,
                        msg=f"{spec.scenario_id} ancestry={ancestry_res}",
                    )

    def test_ancestry_only_fails_open_on_trailing_commit(self) -> None:
        trailing_specs = [s for s in get_proof_scenarios() if s.category == "trailing_commit"]
        self.assertEqual(len(trailing_specs), 3)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in trailing_specs:
                ctx = materialize_scenario(spec, root)
                naive_res = verify_naive_status_only(ctx.proof_path)
                ancestry_res = verify_ancestry_only(ctx.repo_dir, ctx.proof_path)
                strict_res = verify_strict_commit_bound(
                    ctx.repo_dir,
                    ctx.proof_path,
                    expected_branch=ctx.expected_branch,
                )
                self.assertTrue(naive_res.passed)
                self.assertTrue(ancestry_res.passed)
                self.assertFalse(strict_res.passed)
                self.assertTrue(
                    any("HEAD commit mismatch" in reason for reason in strict_res.reasons),
                    msg=f"Expected HEAD mismatch reason, got {strict_res.reasons}",
                )

    def test_cross_model_can_be_disabled_when_explicitly_opted_out(self) -> None:
        spec = next(
            s for s in get_proof_scenarios() if s.scenario_id == "same_model_family_violation"
        )
        with tempfile.TemporaryDirectory() as tmp:
            ctx = materialize_scenario(spec, Path(tmp))
            strict_default = verify_strict_commit_bound(
                ctx.repo_dir, ctx.proof_path, expected_branch=ctx.expected_branch
            )
            strict_no_cross = verify_strict_commit_bound(
                ctx.repo_dir,
                ctx.proof_path,
                expected_branch=ctx.expected_branch,
                require_cross_model=False,
            )
            self.assertFalse(strict_default.passed)
            self.assertTrue(strict_no_cross.passed)


class TestNegativeRoutingClassifier(unittest.TestCase):
    """Verify deterministic tier routing against run-spec negative routing rules."""

    def test_deterministic_boundary_classifier_matches_all_samples(self) -> None:
        samples = get_routing_samples()
        self.assertEqual(len(samples), 16)

        for sample in samples:
            with self.subTest(sample=sample.sample_id):
                decision = classify_execution_tier(
                    sample.changed_files,
                    sample.diff_text,
                    has_regression_test=sample.has_regression_test,
                    classifier="deterministic_boundary",
                )
                self.assertEqual(
                    decision.tier,
                    sample.expected_tier,
                    msg=f"{sample.sample_id}: {decision}",
                )
                self.assertTrue(decision.negative_route_checked)

    def test_empty_changed_files_fails_safe_to_full_assurance(self) -> None:
        decision = classify_execution_tier([], "", classifier="deterministic_boundary")
        self.assertEqual(decision.tier, "full-assurance")

    def test_candidate_proof_schema_matches_gate_contract(self) -> None:
        schema_path = HERE.parent / "proof.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected_required = set(REQUIRED_CORE_FIELDS) | set(REQUIRED_ATTESTATION_FIELDS)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]), set(ALLOWED_PROOF_FIELDS))
        self.assertEqual(set(schema["required"]), expected_required)
        self.assertEqual(
            schema["properties"]["target_commit_sha"]["pattern"],
            CANONICAL_SHA_RE.pattern,
        )
        for field in (
            "run_id",
            "staging_host",
            "replay_command",
            "author_id",
            "reviewer_id",
            "author_model_family",
            "reviewer_model_family",
        ):
            self.assertEqual(
                schema["properties"][field].get("pattern"),
                r"\S",
                msg=f"Schema field {field} must enforce non-whitespace pattern",
            )

    def test_strict_gate_rejects_extra_fields_whitespace_and_empty_model_family(self) -> None:
        spec = next(s for s in get_proof_scenarios() if s.scenario_id == "clean_commit_python")
        with tempfile.TemporaryDirectory() as tmp:
            ctx = materialize_scenario(spec, Path(tmp))
            base_payload = json.loads(ctx.proof_path.read_text(encoding="utf-8"))

            # 1. Unexpected extra key violates additionalProperties: false
            extra_proof = Path(tmp) / "extra_proof.json"
            extra_proof.write_text(
                json.dumps({**base_payload, "override_bypass": True}),
                encoding="utf-8",
            )
            extra_res = verify_strict_commit_bound(
                ctx.repo_dir, extra_proof, expected_branch=ctx.expected_branch
            )
            self.assertFalse(extra_res.passed)
            self.assertTrue(any("unexpected proof fields" in r for r in extra_res.reasons))

            # 2. Whitespace-only strings fail strict validation across string fields
            for field in (
                "run_id",
                "replay_command",
                "author_id",
                "reviewer_id",
                "staging_host",
            ):
                ws_proof = Path(tmp) / f"ws_{field}.json"
                ws_proof.write_text(
                    json.dumps({**base_payload, field: "   "}),
                    encoding="utf-8",
                )
                ws_res = verify_strict_commit_bound(
                    ctx.repo_dir, ws_proof, expected_branch=ctx.expected_branch
                )
                self.assertFalse(ws_res.passed, msg=f"Whitespace {field} unexpectedly passed")

            # 3. Empty/non-string model families fail even when require_cross_model=False
            for field in ("author_model_family", "reviewer_model_family"):
                for bad_val in ("   ", 123):
                    bad_proof = Path(tmp) / f"bad_{field}_{type(bad_val).__name__}.json"
                    bad_proof.write_text(
                        json.dumps({**base_payload, field: bad_val}),
                        encoding="utf-8",
                    )
                    res = verify_strict_commit_bound(
                        ctx.repo_dir,
                        bad_proof,
                        expected_branch=ctx.expected_branch,
                        require_cross_model=False,
                    )
                    self.assertFalse(
                        res.passed,
                        msg=f"Invalid {field}={bad_val!r} passed with require_cross_model=False",
                    )


if __name__ == "__main__":
    unittest.main()
