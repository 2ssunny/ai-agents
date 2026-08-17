"""Behavioural tests for the verification and completion machinery.

These test what the audit actually decides, not whether files exist. Each test
builds a real working directory, introduces one specific defect, and asserts the
audit refuses to pass — and, just as importantly, that the undamaged fixture does
pass, so the gates are not simply always-fail.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(TESTS_DIR))

import fixture_builder as fx  # noqa: E402
from _lib import (  # noqa: E402
    SETTLED_STATUSES,
    UNRESOLVED_STATUSES,
    VERIFICATION_STATUSES,
    load_json,
    load_schema,
    save_json,
    validate_instance,
)
from final_audit import audit  # noqa: E402


class FixtureCase(unittest.TestCase):
    """Base class providing a throwaway directory per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def build(self, variant: str) -> Path:
        """Materialise a fixture variant."""
        return fx.VARIANTS[variant](self.root / variant)

    def audit_variant(self, variant: str) -> dict:
        """Materialise a variant and audit it."""
        return audit(self.build(variant), profile_override=None, require_human_review=False)

    def failing_gates(self, result: dict) -> set[str]:
        """Return the IDs of mandatory gates that failed."""
        return {
            gate["gate_id"]
            for gate in result["gates"]
            if gate["mandatory"] and not gate["passed"]
        }


class TestAuditPassesOnValidWork(FixtureCase):
    """The audit must be capable of passing, or every other test is meaningless."""

    def test_minimal_valid_fixture_passes(self) -> None:
        result = self.audit_variant("minimal-valid")
        self.assertEqual(result["verdict"], "pass", msg=result["failures"])
        self.assertEqual(result["failures"], [])

    def test_summary_counts_are_honest(self) -> None:
        result = self.audit_variant("minimal-valid")
        summary = result["summary"]
        self.assertEqual(summary["examples_total"], 1)
        self.assertEqual(summary["records_present"], 1)
        self.assertEqual(summary["settled_records"], 1)
        self.assertEqual(summary["stale_records"], 0)

    def test_human_review_is_not_implied_by_automated_checks(self) -> None:
        """Passing preflight must never be reported as a human having looked."""
        result = self.audit_variant("minimal-valid")
        self.assertFalse(result["summary"]["human_visual_review_recorded"])
        self.assertIn("PDF structural preflight", result["summary"]["automated_checks_only"])

    def test_human_review_gate_is_advisory_by_default_and_mandatory_on_request(self) -> None:
        work_dir = self.build("minimal-valid")
        relaxed = audit(work_dir, None, require_human_review=False)
        strict = audit(work_dir, None, require_human_review=True)
        self.assertEqual(relaxed["verdict"], "pass")
        self.assertEqual(strict["verdict"], "fail")
        self.assertIn("human_visual_review_recorded", self.failing_gates(strict))


class TestFalseVerification(FixtureCase):
    """A settled status must be impossible without the evidence behind it."""

    def test_verified_without_evidence_is_rejected(self) -> None:
        result = self.audit_variant("missing-evidence")
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("verification_evidence_complete", self.failing_gates(result))
        self.assertTrue(
            any("no evidence" in failure for failure in result["failures"]),
            msg=result["failures"],
        )

    def test_verified_with_a_required_check_missing_is_rejected(self) -> None:
        result = self.audit_variant("missing-check")
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(
            any("energy_balance" in failure for failure in result["failures"]),
            msg=result["failures"],
        )

    def test_unresolved_item_included_as_finished_is_rejected(self) -> None:
        result = self.audit_variant("unresolved-as-verified")
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("no_unresolved_presented_as_verified", self.failing_gates(result))

    def test_evidence_path_must_exist_on_disk(self) -> None:
        work_dir = self.build("minimal-valid")
        (work_dir / "verification" / f"{fx.EXAMPLE_ID}-recompute.md").unlink()
        result = audit(work_dir, None, require_human_review=False)
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("verification_evidence_complete", self.failing_gates(result))

    def test_not_applicable_check_needs_a_reason(self) -> None:
        """`not_applicable` without a note is an unexplained gap, not a pass."""
        work_dir = self.build("minimal-valid")
        record_path = work_dir / "solution-records" / "REC-001.json"
        record = load_json(record_path)
        for check in record["checks"]:
            if check["check_id"] == "official_solution_compared":
                check["note"] = None
        save_json(record_path, record)
        result = audit(work_dir, None, require_human_review=False)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(
            any("without a note" in failure for failure in result["failures"]),
            msg=result["failures"],
        )


class TestStaleness(FixtureCase):
    """Editing verified text must invalidate the verification, not survive it."""

    def test_editing_canonical_text_makes_the_record_stale(self) -> None:
        result = self.audit_variant("stale-content")
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("no_stale_verification_records", self.failing_gates(result))
        self.assertEqual(result["summary"]["stale_records"], 1)

    def test_reverification_after_an_edit_restores_the_pass(self) -> None:
        """The text stays editable: fix the record's hash and the audit passes again."""
        work_dir = self.build("stale-content")
        self.assertEqual(audit(work_dir, None, False)["verdict"], "fail")

        record_path = work_dir / "solution-records" / "REC-001.json"
        record = load_json(record_path)
        record["content_hash"]["value"] = fx.current_block_hash(work_dir, fx.EXAMPLE_ID)
        save_json(record_path, record)

        self.assertEqual(audit(work_dir, None, False)["verdict"], "pass")

    def test_removing_the_verified_block_is_detected(self) -> None:
        work_dir = self.build("minimal-valid")
        path = work_dir / "canonical-content" / f"{fx.CHAPTER_ID}.md"
        without_example = path.read_text(encoding="utf-8").split(
            f"<!-- id: {fx.EXAMPLE_ID}"
        )[0] + f"<!-- end: {fx.CHAPTER_ID} -->\n"
        path.write_text(without_example, encoding="utf-8")
        result = audit(work_dir, None, require_human_review=False)
        self.assertEqual(result["verdict"], "fail")


class TestCompletionGates(FixtureCase):
    """Each mandatory gate must actually block completion."""

    def test_missing_approval_blocks_completion(self) -> None:
        result = self.audit_variant("missing-approval")
        self.assertIn("outline_approved", self.failing_gates(result))

    def test_missing_artifact_blocks_completion(self) -> None:
        result = self.audit_variant("missing-artifact")
        self.assertIn("required_artifacts_present", self.failing_gates(result))

    def test_unexecuted_preflight_blocks_completion(self) -> None:
        result = self.audit_variant("no-preflight")
        self.assertIn("pdf_preflight_executed", self.failing_gates(result))

    def test_wrong_reported_page_count_blocks_completion(self) -> None:
        result = self.audit_variant("page-count-mismatch")
        self.assertIn("page_counts_match_actual", self.failing_gates(result))
        self.assertTrue(
            any("reported 42 pages, file has 2" in failure for failure in result["failures"]),
            msg=result["failures"],
        )

    def test_divergent_language_editions_block_completion(self) -> None:
        result = self.audit_variant("parity-mismatch")
        self.assertIn("language_editions_in_parity", self.failing_gates(result))

    def test_english_only_project_is_exempt_from_parity(self) -> None:
        """A project that never declares a bilingual artefact has nothing to compare."""
        work_dir = self.build("minimal-valid")
        shutil.rmtree(work_dir / "editions" / "bilingual")
        result = audit(work_dir, None, require_human_review=False)
        self.assertNotIn("language_editions_in_parity", self.failing_gates(result))
        self.assertEqual(result["verdict"], "pass", msg=result["failures"])

    def test_declared_bilingual_artifact_without_its_source_fails(self) -> None:
        """The exemption cannot be obtained by deleting the edition source."""
        work_dir = self.build("minimal-valid")
        shutil.rmtree(work_dir / "editions" / "bilingual")
        state = load_json(work_dir / "progress.json")
        state["artifacts"].append(
            {
                "artifact_id": "notes_ko",
                "kind": "notes_bilingual",
                "path": "output/notes-en.pdf",
                "language": "ko-en",
                "format": "md",
                "reported_page_count": None,
                "source_files": [],
            }
        )
        save_json(work_dir / "progress.json", state)
        result = audit(work_dir, None, require_human_review=False)
        self.assertIn("language_editions_in_parity", self.failing_gates(result))

    def test_progress_claiming_complete_while_a_gate_fails_is_itself_a_failure(self) -> None:
        result = self.audit_variant("no-preflight")
        self.assertIn("progress_matches_reality", self.failing_gates(result))

    def test_outline_only_project_is_not_complete(self) -> None:
        """A skeleton with no worked examples must never audit as finished."""
        work_dir = self.build("minimal-valid")
        (work_dir / "canonical-content" / f"{fx.CHAPTER_ID}.md").unlink()
        (work_dir / "canonical-content" / f"{fx.CHAPTER_ID}.json").unlink()
        result = audit(work_dir, None, require_human_review=False)
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("canonical_content_complete", self.failing_gates(result))

    def test_audit_result_conforms_to_its_schema(self) -> None:
        result = self.audit_variant("minimal-valid")
        self.assertEqual(validate_instance(result, load_schema("final-audit"), "audit"), [])


class TestStatusVocabulary(unittest.TestCase):
    """The status vocabulary must stay closed and correctly partitioned."""

    def test_schema_and_library_agree_on_the_status_list(self) -> None:
        schema = load_schema("verification-record")
        self.assertEqual(
            tuple(schema["properties"]["status"]["enum"]), VERIFICATION_STATUSES
        )

    def test_settled_and_unresolved_partition_the_vocabulary(self) -> None:
        self.assertEqual(SETTLED_STATUSES & UNRESOLVED_STATUSES, set())
        self.assertEqual(
            SETTLED_STATUSES | UNRESOLVED_STATUSES, set(VERIFICATION_STATUSES)
        )

    def test_an_invented_status_is_rejected(self) -> None:
        record = fx._record()
        record["status"] = "PROBABLY_FINE"
        errors = validate_instance(record, load_schema("verification-record"), "r")
        self.assertTrue(any("PROBABLY_FINE" in error for error in errors), msg=errors)

    def test_schema_alone_rejects_a_settled_status_without_evidence(self) -> None:
        """Structural rejection, independent of verify_evidence's semantic checks."""
        record = fx._record()
        record["evidence"] = []
        errors = validate_instance(record, load_schema("verification-record"), "r")
        self.assertTrue(errors, msg="schema accepted VERIFIED with no evidence")

    def test_schema_allows_an_unresolved_record_without_evidence(self) -> None:
        record = fx._record(status="NOT_YET_VERIFIED", verified_at=None, verified_by=None)
        record["evidence"] = []
        record["checks"] = []
        self.assertEqual(validate_instance(record, load_schema("verification-record"), "r"), [])


if __name__ == "__main__":
    unittest.main()
