"""Behavioural tests for progress state, profiles and the SKILL.md contract."""

from __future__ import annotations

import re
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
    PHASES,
    PROGRESS_STATES,
    Report,
    load_schema,
    load_yaml,
    read_text,
    save_json,
    validate_instance,
)
from validate_profile import check_profile  # noqa: E402
from validate_state import check_no_regression, check_state  # noqa: E402

PROFILE_DIR = SKILL_DIR / "profiles"
REQUIRED_PROFILES = ("generic-stem", "thermodynamics", "structures")


class TempCase(unittest.TestCase):
    """Base class providing a throwaway directory per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class TestProfiles(unittest.TestCase):
    """Every shipped profile must define a usable verification contract."""

    def test_all_required_profiles_exist_and_validate(self) -> None:
        for name in REQUIRED_PROFILES:
            with self.subTest(profile=name):
                path = PROFILE_DIR / f"{name}.yaml"
                self.assertTrue(path.is_file(), f"{path} is missing")
                report = Report(check="t")
                check_profile(load_yaml(path), path.name, report)
                self.assertEqual(report.failures, [], msg=report.failures)

    def test_profile_id_matches_its_filename(self) -> None:
        """verify_evidence resolves a bundled profile by filename from profile_id."""
        for name in REQUIRED_PROFILES:
            with self.subTest(profile=name):
                self.assertEqual(load_yaml(PROFILE_DIR / f"{name}.yaml")["profile_id"], name)

    def test_subject_profiles_extend_the_generic_contract(self) -> None:
        generic = {
            check["check_id"]
            for check in load_yaml(PROFILE_DIR / "generic-stem.yaml")["required_checks"]
        }
        for name in ("thermodynamics", "structures"):
            with self.subTest(profile=name):
                subject = {
                    check["check_id"]
                    for check in load_yaml(PROFILE_DIR / f"{name}.yaml")["required_checks"]
                }
                self.assertTrue(
                    generic <= subject,
                    f"{name} drops generic checks: {sorted(generic - subject)}",
                )

    def test_subject_profiles_add_their_own_checks(self) -> None:
        generic = {
            check["check_id"]
            for check in load_yaml(PROFILE_DIR / "generic-stem.yaml")["required_checks"]
        }
        for name, expected in (
            ("thermodynamics", "energy_balance"),
            ("structures", "second_moment_orientation"),
        ):
            with self.subTest(profile=name):
                subject = {
                    check["check_id"]
                    for check in load_yaml(PROFILE_DIR / f"{name}.yaml")["required_checks"]
                }
                self.assertTrue(subject - generic)
                self.assertIn(expected, subject)

    def test_profile_missing_required_fields_is_rejected(self) -> None:
        report = Report(check="t")
        check_profile({"profile_id": "broken"}, "broken.yaml", report)
        self.assertTrue(report.failures)

    def test_check_listed_as_both_required_and_optional_is_rejected(self) -> None:
        profile = load_yaml(PROFILE_DIR / "generic-stem.yaml")
        profile["optional_checks"] = [
            {"check_id": "energy_balance_dup", "title": "x"},
            {"check_id": "units_and_dimensions", "title": "duplicate of a required check"},
        ]
        report = Report(check="t")
        check_profile(profile, "clash.yaml", report)
        self.assertTrue(
            any("both required and optional" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_inconsistent_page_targets_are_rejected(self) -> None:
        profile = load_yaml(PROFILE_DIR / "generic-stem.yaml")
        profile["page_targets"]["preferred_min_pages"] = 999
        report = Report(check="t")
        check_profile(profile, "pages.yaml", report)
        self.assertTrue(
            any("preferred_min_pages" in failure for failure in report.failures),
            msg=report.failures,
        )


class TestProgressState(TempCase):
    """The checkpoint must not be able to lie about where the work stands."""

    def test_valid_fixture_state_passes(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "valid")
        report = Report(check="t")
        check_state(fx._progress(), work_dir, report)
        self.assertEqual(report.failures, [], msg=report.failures)

    def test_complete_with_a_failing_gate_is_rejected(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "gate")
        state = fx._progress()
        state["completion_gates"]["pdf_preflight_executed"] = False
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertTrue(
            any("pdf_preflight_executed" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_drafting_before_approval_is_rejected(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "approval")
        state = fx._progress()
        state["current_phase"] = "phase3_canonical_content"
        state["approval"] = {"outline_approved": False, "approved_at": None, "approved_by": None}
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertTrue(
            any("before the outline is approved" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_counts_must_match_the_records_on_disk(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "counts")
        state = fx._progress()
        state["counts"]["settled_records"] = 40
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertTrue(
            any("settled_records" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_unknown_state_value_is_rejected(self) -> None:
        state = fx._progress()
        state["state"] = "nearly_done"
        errors = validate_instance(state, load_schema("progress-state"), "progress")
        self.assertTrue(any("nearly_done" in error for error in errors), msg=errors)

    def test_state_vocabulary_matches_the_schema(self) -> None:
        schema = load_schema("progress-state")
        self.assertEqual(tuple(schema["properties"]["state"]["enum"]), PROGRESS_STATES)
        self.assertEqual(tuple(schema["properties"]["current_phase"]["enum"]), PHASES)

    def test_human_review_claimed_without_a_reviewer_is_rejected(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "review")
        state = fx._progress()
        state["visual_review"]["human_visual_review_recorded"] = True
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertTrue(
            any("no human_reviewer is named" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_heuristics_cannot_pass_on_pages_that_were_never_rendered(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "heur")
        state = fx._progress()
        state["visual_review"]["automated_visual_heuristics_passed"] = True
        state["visual_review"]["rendered_pages_generated"] = False
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertTrue(report.failures)


class TestCheckpointRecovery(TempCase):
    """A checkpoint must never quietly replace a more complete one."""

    def test_regressing_record_counts_is_rejected(self) -> None:
        previous = fx._progress()
        current = fx._progress()
        current["counts"]["settled_records"] = 0
        report = Report(check="t")
        check_no_regression(current, previous, report)
        self.assertTrue(
            any("never overwrite the latest valid checkpoint" in f for f in report.failures),
            msg=report.failures,
        )

    def test_dropping_a_completed_phase_is_rejected(self) -> None:
        previous = fx._progress()
        current = fx._progress()
        current["completed_phases"] = ["phase0_environment"]
        report = Report(check="t")
        check_no_regression(current, previous, report)
        self.assertTrue(report.failures)

    def test_dropping_a_recorded_approval_is_rejected(self) -> None:
        previous = fx._progress()
        current = fx._progress()
        current["approval"]["outline_approved"] = False
        report = Report(check="t")
        check_no_regression(current, previous, report)
        self.assertTrue(
            any("drops" in failure for failure in report.failures), msg=report.failures
        )

    def test_progressing_forward_is_allowed(self) -> None:
        previous = fx._progress()
        current = fx._progress()
        current["counts"]["settled_records"] = 5
        current["counts"]["records_present"] = 5
        report = Report(check="t")
        check_no_regression(current, previous, report)
        self.assertEqual(report.failures, [])

    def test_recovery_reads_real_progress_not_the_presence_of_a_pdf(self) -> None:
        """A finished-looking PDF next to an unfinished checkpoint is still unfinished."""
        work_dir = fx.build_minimal_valid(self.root / "recover")
        state = fx._progress()
        state["state"] = "in_progress"
        state["counts"] = {
            "expected_problems": 40,
            "records_present": 1,
            "settled_records": 1,
            "unresolved_records": 0,
        }
        save_json(work_dir / "progress.json", state)
        report = Report(check="t")
        check_state(state, work_dir, report)
        self.assertEqual(report.failures, [], msg=report.failures)
        self.assertLess(state["counts"]["records_present"], state["counts"]["expected_problems"])


class TestSkillDocument(unittest.TestCase):
    """SKILL.md must stay valid and portable across agents."""

    #: Fields any Agent Skills implementation understands.
    ALLOWED_FRONTMATTER_KEYS = {"name", "description"}

    def setUp(self) -> None:
        self.text = read_text(SKILL_DIR / "SKILL.md")

    def frontmatter(self) -> dict[str, str]:
        """Parse the YAML frontmatter block."""
        match = re.match(r"^---\n(.*?)\n---\n", self.text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must open with a --- frontmatter block")
        import yaml

        parsed = yaml.safe_load(match.group(1))
        self.assertIsInstance(parsed, dict)
        return parsed

    def test_frontmatter_has_name_and_description(self) -> None:
        data = self.frontmatter()
        self.assertEqual(data["name"], "exam-prep")
        self.assertTrue(data["description"].strip())

    def test_frontmatter_uses_no_platform_exclusive_fields(self) -> None:
        extra = set(self.frontmatter()) - self.ALLOWED_FRONTMATTER_KEYS
        self.assertEqual(extra, set(), f"platform-specific frontmatter keys: {sorted(extra)}")

    def test_description_names_the_activation_material(self) -> None:
        description = self.frontmatter()["description"].lower()
        for trigger in ("past paper", "lecture", "revision", "worked", "bilingual"):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, description)

    def test_body_covers_every_mandatory_section(self) -> None:
        for heading in (
            "Activation",
            "Workflow",
            "Approval",
            "Verification",
            "Recovery",
            "Completion gates",
            "Honesty rules",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.text)

    def test_every_referenced_document_exists(self) -> None:
        links = re.findall(r"\]\((references/[A-Za-z0-9._/-]+)\)", self.text)
        self.assertTrue(links, "SKILL.md should link its reference documents")
        for link in sorted(set(links)):
            with self.subTest(link=link):
                self.assertTrue((SKILL_DIR / link).is_file(), f"{link} does not exist")

    def test_every_referenced_script_exists(self) -> None:
        names = re.findall(r"scripts/([a-z_]+\.py)", self.text)
        for name in sorted(set(names)):
            with self.subTest(script=name):
                self.assertTrue((SKILL_DIR / "scripts" / name).is_file())

    def test_stays_short_enough_for_progressive_disclosure(self) -> None:
        lines = len(self.text.splitlines())
        self.assertLess(lines, 260, f"SKILL.md is {lines} lines; move detail into references/")

    def test_no_absolute_user_paths_are_committed(self) -> None:
        for pattern in (r"C:\\Users\\", r"/home/[a-z]+/", r"/Users/[a-z]+/"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.text))


if __name__ == "__main__":
    unittest.main()
