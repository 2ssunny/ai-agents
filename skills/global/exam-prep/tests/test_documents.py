"""Behavioural tests for the document-side checks.

Covers canonical block parsing, cross-language parity, English-only Hangul
detection and PDF preflight — including the case the whole design exists to
prevent: a reported page count that the file does not support.
"""

from __future__ import annotations

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
    Report,
    SkillError,
    contains_hangul,
    find_replacement_characters,
    hangul_positions,
    parse_blocks,
    visible_character_count,
)
from check_english_only import scan_file  # noqa: E402
from check_parity import check_numerical_parity, collect_blocks, compare  # noqa: E402
from pdf_preflight import preflight  # noqa: E402
from pdf_text import pdf_page_count, stdlib_page_count  # noqa: E402


class TempCase(unittest.TestCase):
    """Base class providing a throwaway directory per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class TestBlockParsing(unittest.TestCase):
    """Canonical IDs are anchored in plain Markdown and must parse exactly."""

    def test_nested_blocks_are_parsed_with_parents(self) -> None:
        blocks = {block.block_id: block for block in parse_blocks(fx.CHAPTER_MARKDOWN)}
        self.assertEqual(blocks[fx.EXAMPLE_ID].parent_id, fx.CHAPTER_ID)
        self.assertEqual(blocks[fx.EQUATION_ID].parent_id, fx.SECTION_ID)
        self.assertEqual(blocks[fx.EXAMPLE_ID].kind, "worked_example")

    def test_unclosed_block_is_an_error(self) -> None:
        with self.assertRaises(SkillError):
            parse_blocks("<!-- id: CH-01 kind: chapter -->\n# hi\n")

    def test_mismatched_end_marker_is_an_error(self) -> None:
        with self.assertRaises(SkillError):
            parse_blocks(
                "<!-- id: CH-01 kind: chapter -->\n<!-- end: CH-02 -->\n"
            )

    def test_duplicate_ids_are_an_error(self) -> None:
        with self.assertRaises(SkillError):
            parse_blocks(
                "<!-- id: CH-01 kind: chapter -->\n<!-- end: CH-01 -->\n"
                "<!-- id: CH-01 kind: chapter -->\n<!-- end: CH-01 -->\n"
            )

    def test_block_hash_changes_when_the_body_changes(self) -> None:
        original = parse_blocks(fx.CHAPTER_MARKDOWN)[0]
        edited = parse_blocks(fx.CHAPTER_MARKDOWN.replace("1400 kW", "1750 kW"))[0]
        self.assertNotEqual(original.content_hash, edited.content_hash)

    def test_block_hash_ignores_line_ending_style(self) -> None:
        unix = parse_blocks(fx.CHAPTER_MARKDOWN)[0]
        windows = parse_blocks(fx.CHAPTER_MARKDOWN.replace("\n", "\r\n"))[0]
        self.assertEqual(unix.content_hash, windows.content_hash)


class TestParity(TempCase):
    """The two editions may differ in prose but never in canonical identifiers."""

    def test_matching_editions_are_in_parity(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "valid")
        report = Report(check="t")
        compare(
            collect_blocks(work_dir / "editions" / "english"),
            collect_blocks(work_dir / "editions" / "bilingual"),
            report,
        )
        self.assertEqual(report.failures, [])

    def test_missing_id_in_one_edition_is_reported(self) -> None:
        work_dir = fx.build_parity_mismatch(self.root / "mismatch")
        report = Report(check="t")
        compare(
            collect_blocks(work_dir / "editions" / "english"),
            collect_blocks(work_dir / "editions" / "bilingual"),
            report,
        )
        self.assertTrue(any(fx.EXAMPLE_ID in failure for failure in report.failures))

    def test_reordered_content_is_reported(self) -> None:
        english = "\n".join(
            [
                "<!-- id: SEC-01-01 kind: section -->",
                "<!-- end: SEC-01-01 -->",
                "<!-- id: SEC-01-02 kind: section -->",
                "<!-- end: SEC-01-02 -->",
            ]
        )
        bilingual = "\n".join(
            [
                "<!-- id: SEC-01-02 kind: section -->",
                "<!-- end: SEC-01-02 -->",
                "<!-- id: SEC-01-01 kind: section -->",
                "<!-- end: SEC-01-01 -->",
            ]
        )
        report = Report(check="t")
        compare(parse_blocks(english), parse_blocks(bilingual), report)
        self.assertTrue(
            any("ordering differs" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_numerical_result_missing_from_an_edition_is_reported(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "numbers")
        report = Report(check="t")
        check_numerical_parity(
            work_dir / "canonical-content",
            "Wdot = 1400 kW",
            "Wdot = 1750 kW",  # bilingual edition carries a different number
            report,
        )
        self.assertTrue(
            any("bilingual edition" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_identical_numbers_pass(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "numbers-ok")
        report = Report(check="t")
        check_numerical_parity(
            work_dir / "canonical-content", "Wdot = 1400 kW", "Wdot = 1400 kW", report
        )
        self.assertEqual(report.failures, [])


class TestHangulDetection(TempCase):
    """The English edition must be free of Korean text."""

    def test_hangul_is_detected_with_a_location(self) -> None:
        occurrences = hangul_positions("line one\nadiabatic turbine (단열 터빈)\n")
        self.assertEqual(len(occurrences), 2)
        self.assertEqual(occurrences[0][0], 2)
        self.assertEqual(occurrences[0][2], "단열")

    def test_pure_english_has_no_hangul(self) -> None:
        self.assertFalse(contains_hangul("Wdot = 1400 kW, adiabatic turbine"))

    def test_jamo_and_syllables_both_count(self) -> None:
        self.assertTrue(contains_hangul("ㄱ"))
        self.assertTrue(contains_hangul("가"))

    def test_english_edition_fixture_is_clean(self) -> None:
        work_dir = fx.build_minimal_valid(self.root / "clean")
        report = Report(check="t")
        scan_file(work_dir / "editions" / "english" / f"{fx.CHAPTER_ID}.md", 40, report)
        self.assertEqual(report.failures, [])

    def test_leaked_korean_in_the_english_edition_is_caught(self) -> None:
        work_dir = fx.build_hangul_in_english(self.root / "leak")
        report = Report(check="t")
        scan_file(work_dir / "editions" / "english" / f"{fx.CHAPTER_ID}.md", 40, report)
        self.assertTrue(report.failures)

    def test_bilingual_edition_is_expected_to_contain_hangul(self) -> None:
        """Guards against a check that would flag correct bilingual output."""
        work_dir = fx.build_minimal_valid(self.root / "bilingual")
        text = (work_dir / "editions" / "bilingual" / f"{fx.CHAPTER_ID}.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(contains_hangul(text))


class TestTextHeuristics(unittest.TestCase):
    """Blank-page and broken-glyph heuristics."""

    def test_replacement_characters_are_found(self) -> None:
        hits = find_replacement_characters("fine line\nbroken � glyph\n")
        self.assertEqual(hits[0][0], 2)

    def test_whitespace_only_page_counts_as_blank(self) -> None:
        self.assertEqual(visible_character_count("   \n\t \n"), 0)

    def test_real_text_is_not_blank(self) -> None:
        self.assertGreater(visible_character_count("Wdot = 1400 kW"), 10)


class TestPdfPreflight(TempCase):
    """Page counts must come from the file, never from a claim about it."""

    def test_generated_fixture_pdf_is_readable(self) -> None:
        pdf = self.root / "notes.pdf"
        fx.write_minimal_pdf(pdf, fx.NOTES_PDF_PAGES)
        count, detail = pdf_page_count(pdf)
        self.assertEqual(count, len(fx.NOTES_PDF_PAGES), msg=detail)

    def test_stdlib_fallback_agrees_with_the_page_tree(self) -> None:
        pdf = self.root / "five.pdf"
        fx.write_minimal_pdf(pdf, [[f"page {n}"] for n in range(1, 6)])
        count, detail = stdlib_page_count(pdf)
        self.assertEqual(count, 5, msg=detail)

    def test_stdlib_fallback_refuses_to_guess_on_an_unparseable_file(self) -> None:
        broken = self.root / "broken.pdf"
        broken.write_bytes(b"%PDF-1.4\nnot really a pdf\n%%EOF\n")
        count, detail = stdlib_page_count(broken)
        self.assertIsNone(count)
        self.assertIn("could not read", detail)

    def test_preflight_passes_on_a_sound_pdf(self) -> None:
        pdf = self.root / "notes.pdf"
        fx.write_minimal_pdf(pdf, fx.NOTES_PDF_PAGES)
        report = Report(check="t")
        result = preflight(pdf, report)
        self.assertEqual(report.failures, [], msg=report.failures)
        self.assertEqual(result["actual_page_count"], len(fx.NOTES_PDF_PAGES))

    def test_preflight_rejects_a_wrong_reported_page_count(self) -> None:
        pdf = self.root / "notes.pdf"
        fx.write_minimal_pdf(pdf, fx.NOTES_PDF_PAGES)
        report = Report(check="t")
        preflight(pdf, report, expect_pages=118)
        self.assertTrue(
            any("does not match the actual" in failure for failure in report.failures),
            msg=report.failures,
        )

    def test_preflight_accepts_a_correct_reported_page_count(self) -> None:
        pdf = self.root / "notes.pdf"
        fx.write_minimal_pdf(pdf, fx.NOTES_PDF_PAGES)
        report = Report(check="t")
        preflight(pdf, report, expect_pages=len(fx.NOTES_PDF_PAGES))
        self.assertEqual(report.failures, [])

    def test_missing_file_fails_rather_than_passing_silently(self) -> None:
        report = Report(check="t")
        preflight(self.root / "absent.pdf", report)
        self.assertTrue(any("does not exist" in failure for failure in report.failures))

    def test_truncated_output_is_rejected(self) -> None:
        tiny = self.root / "tiny.pdf"
        tiny.write_bytes(b"%PDF-1.4\n%%EOF\n")
        report = Report(check="t")
        preflight(tiny, report)
        self.assertTrue(report.failures)

    def test_writing_a_text_sidecar_keeps_the_output_inspectable(self) -> None:
        work_dir = self.root / "work"
        pdf = self.root / "notes.pdf"
        fx.write_minimal_pdf(pdf, fx.NOTES_PDF_PAGES)
        report = Report(check="t")
        result = preflight(pdf, report, work_dir=work_dir)
        if not result.get("page_text_available"):
            self.skipTest("no PDF text reader installed; sidecar generation not exercised")
        self.assertTrue(Path(result["sidecar"]).is_file())


if __name__ == "__main__":
    unittest.main()
