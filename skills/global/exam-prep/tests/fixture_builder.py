"""Build exam-prep working-directory fixtures.

Fixtures are generated rather than committed so that nothing in the repository
looks like real course material, and so the PDFs used by the tests are genuinely
valid files rather than stand-ins.

Each variant is a complete working directory. `minimal-valid` passes the final
audit; every other variant introduces exactly one defect so a test can prove the
audit catches it.

Run directly to materialise a fixture for manual inspection::

    python3 fixture_builder.py --variant minimal-valid --dest /tmp/fixture
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _lib import (  # noqa: E402
    block_index,
    parse_blocks,
    save_json,
    sha256_text,
    write_text,
)

TIMESTAMP = "2026-01-15T09:00:00+00:00"

CHAPTER_ID = "CH-01"
EXAMPLE_ID = "WE-01-01"
EQUATION_ID = "EQ-01-01"
SECTION_ID = "SEC-01-01"

#: PDF page size in points (A4).
PAGE_WIDTH_PT = 595
PAGE_HEIGHT_PT = 842


# --------------------------------------------------------------------------
# Minimal valid PDF writer (no third-party dependency)
# --------------------------------------------------------------------------


def write_minimal_pdf(path: Path, page_lines: list[list[str]]) -> None:
    """Write a small but genuinely valid, uncompressed PDF.

    The page tree is left uncompressed so that both real PDF readers and the
    stdlib fallback in ``pdf_text.py`` can count its pages.

    Args:
        path: Destination file.
        page_lines: Text lines for each page; one inner list per page.
    """
    objects: list[bytes] = []
    page_count = len(page_lines)
    font_number = 3 + page_count * 2

    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(page_count))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"))

    for index, lines in enumerate(page_lines):
        content_number = 4 + index * 2
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH_PT} {PAGE_HEIGHT_PT}] "
                f"/Contents {content_number} 0 R "
                f"/Resources << /Font << /F1 {font_number} 0 R >> >> >>"
            ).encode("ascii")
        )
        stream = _text_stream(lines)
        header = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>"
        objects.append(header + b"\nstream\n" + stream + b"\nendstream")

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    out += trailer.encode("ascii")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


def _text_stream(lines: list[str]) -> bytes:
    """Build an uncompressed page content stream for the given lines."""
    parts = ["BT", "/F1 11 Tf", "14 TL", f"1 0 0 1 60 {PAGE_HEIGHT_PT - 70} Tm"]
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        parts.append(f"({escaped}) Tj T*")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


# --------------------------------------------------------------------------
# Canonical content
# --------------------------------------------------------------------------

CHAPTER_MARKDOWN = f"""<!-- id: {CHAPTER_ID} kind: chapter -->
# Chapter 1 — Steady-flow energy balance

<!-- id: {SECTION_ID} kind: section -->
## 1.1 Control volume selection

A control volume is chosen so that every stream crossing it is known.

<!-- id: {EQUATION_ID} kind: formula -->
Qdot - Wdot = mdot * (h2 - h1)
<!-- end: {EQUATION_ID} -->
<!-- end: {SECTION_ID} -->

<!-- id: {EXAMPLE_ID} kind: worked_example -->
### Worked example 1.1

Steam enters an adiabatic turbine at h1 = 3200 kJ/kg and leaves at
h2 = 2500 kJ/kg with mdot = 2.0 kg/s.

Assumptions: adiabatic, steady flow, negligible kinetic and potential energy.

Wdot = mdot * (h1 - h2) = 2.0 * 700 = 1400 kW
<!-- end: {EXAMPLE_ID} -->
<!-- end: {CHAPTER_ID} -->
"""

CHAPTER_SIDECAR: dict[str, Any] = {
    "schema_version": 1,
    "chapter_id": CHAPTER_ID,
    "title_en": "Steady-flow energy balance",
    "title_ko": "정상유동 에너지 수지",
    "learning_objectives": ["Apply the steady-flow energy equation to a turbine."],
    "sections": [
        {
            "section_id": SECTION_ID,
            "title_en": "Control volume selection",
            "title_ko": "검사체적 설정",
        }
    ],
    "formulas": [
        {
            "equation_id": EQUATION_ID,
            "classification": "DS",
            "datasheet_source_id": "SRC-002",
            "statement": "Qdot - Wdot = mdot * (h2 - h1)",
        }
    ],
    "worked_examples": [
        {
            "example_id": EXAMPLE_ID,
            "title_en": "Adiabatic turbine power",
            "past_paper_reference": None,
            "numerical_results": [{"label": "Wdot", "value": "1400", "unit": "kW"}],
        }
    ],
    "source_references": [{"source_id": "SRC-001", "pages": "12-18"}],
}

EDITION_ENGLISH = f"""<!-- id: {CHAPTER_ID} kind: chapter -->
# Chapter 1 — Steady-flow energy balance

<!-- id: {SECTION_ID} kind: section -->
## 1.1 Control volume selection

<!-- id: {EQUATION_ID} kind: formula -->
Qdot - Wdot = mdot * (h2 - h1)   [DS: data sheet]
<!-- end: {EQUATION_ID} -->
<!-- end: {SECTION_ID} -->

<!-- id: {EXAMPLE_ID} kind: worked_example -->
### Worked example 1.1 — adiabatic turbine

Wdot = 2.0 * (3200 - 2500) = 1400 kW
<!-- end: {EXAMPLE_ID} -->
<!-- end: {CHAPTER_ID} -->
"""

EDITION_BILINGUAL = f"""<!-- id: {CHAPTER_ID} kind: chapter -->
# 1장 — Steady-flow energy balance

<!-- id: {SECTION_ID} kind: section -->
## 1.1 Control volume selection (검사체적 설정)

검사체적은 드나드는 모든 stream을 알 수 있게 잡는다.

<!-- id: {EQUATION_ID} kind: formula -->
Qdot - Wdot = mdot * (h2 - h1)   [DS: data sheet]
<!-- end: {EQUATION_ID} -->
<!-- end: {SECTION_ID} -->

<!-- id: {EXAMPLE_ID} kind: worked_example -->
### Worked example 1.1 — adiabatic turbine

adiabatic 가정이므로 Qdot = 0.

Wdot = 2.0 * (3200 - 2500) = 1400 kW
<!-- end: {EXAMPLE_ID} -->
<!-- end: {CHAPTER_ID} -->
"""

NOTES_PDF_PAGES = [
    [
        "Chapter 1 - Steady-flow energy balance",
        "",
        "1.1 Control volume selection",
        "A control volume is chosen so that every stream crossing it is known.",
        "Qdot - Wdot = mdot * (h2 - h1)   [DS: data sheet]",
        "",
        "The boundary must be drawn before any balance is written, because the",
        "terms that appear in the balance follow from where the boundary cuts.",
    ],
    [
        "Worked example 1.1 - adiabatic turbine",
        "",
        "Steam enters at h1 = 3200 kJ/kg and leaves at h2 = 2500 kJ/kg,",
        "with mdot = 2.0 kg/s. The turbine is adiabatic.",
        "",
        "Assumptions: adiabatic, steady flow, negligible KE and PE.",
        "Wdot = mdot * (h1 - h2) = 2.0 * 700 = 1400 kW",
        "",
        "Check: positive work output is expected for a turbine.",
    ],
]


# --------------------------------------------------------------------------
# Fixture assembly
# --------------------------------------------------------------------------


def _record(status: str = "VERIFIED", **overrides: Any) -> dict[str, Any]:
    """Build a solution record for the fixture's single worked example."""
    checks = [
        {"check_id": check_id, "result": "pass", "note": None}
        for check_id in (
            "problem_statement_captured",
            "assumptions_stated",
            "governing_equations_selected",
            "symbolic_derivation_checked",
            "numerical_recomputation",
            "units_and_dimensions",
            "sign_conventions",
            "limiting_behaviour",
            "system_boundary",
            "steady_or_transient",
            "mass_balance",
            "energy_balance",
            "process_relation",
            "state_vs_path",
            "dimensional_consistency",
        )
    ]
    checks.append(
        {
            "check_id": "official_solution_compared",
            "result": "not_applicable",
            "note": "no official solution was supplied for this example",
        }
    )
    checks.append(
        {
            "check_id": "discrepancies_recorded",
            "result": "not_applicable",
            "note": "nothing to compare against, so no discrepancy can arise",
        }
    )

    record: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "REC-001",
        "example_id": EXAMPLE_ID,
        "chapter_id": CHAPTER_ID,
        "profile_id": "thermodynamics",
        "status": status,
        "checks": checks,
        "evidence": [
            {
                "kind": "independent_recomputation",
                "path": "verification/WE-01-01-recompute.md",
                "description": (
                    "Energy balance re-evaluated from h1, h2 and mdot "
                    "without reading any answer."
                ),
                "script_hook": None,
            }
        ],
        "official_solution": {
            "available": False,
            "source_id": None,
            "agreement": "not_available",
            "discrepancy_id": None,
        },
        "content_hash": {
            "algorithm": "sha256",
            "source_file": f"canonical-content/{CHAPTER_ID}.md",
            "block_id": EXAMPLE_ID,
            # Placeholder of the right shape; every builder replaces it with the
            # hash of the block as it actually stands on disk.
            "value": sha256_text(""),
        },
        "assumptions": ["Adiabatic", "Steady flow", "Negligible KE and PE"],
        "unresolved_questions": [],
        "verified_at": TIMESTAMP,
        "verified_by": "agent",
        "notes": None,
    }
    record.update(overrides)
    return record


def _progress(**overrides: Any) -> dict[str, Any]:
    """Build a progress checkpoint that satisfies every mandatory gate."""
    state: dict[str, Any] = {
        "schema_version": 1,
        "project_id": "fixture-thermo",
        "profile_id": "thermodynamics",
        "state": "complete",
        "current_phase": "phase7_qa",
        "completed_phases": list(
            (
                "phase0_environment",
                "phase1_inventory",
                "phase2_scope",
                "phase3_canonical_content",
                "phase4_verification",
                "phase5_generation",
                "phase6_checkpoint",
                "phase7_qa",
            )
        ),
        "approval": {
            "outline_approved": True,
            "approved_at": TIMESTAMP,
            "approved_by": "user",
            "approval_note": "outline approved in session",
        },
        "counts": {
            "expected_problems": 1,
            "records_present": 1,
            "settled_records": 1,
            "unresolved_records": 0,
        },
        "blocking_items": [],
        "unresolved_discrepancies": [],
        "artifacts": [
            {
                "artifact_id": "notes_en",
                "kind": "notes_english",
                "path": "output/notes-en.pdf",
                "language": "en",
                "format": "pdf",
                "reported_page_count": len(NOTES_PDF_PAGES),
                "source_files": ["editions/english/CH-01.md"],
            }
        ],
        "pdf_preflight": {
            "executed": True,
            "executed_at": TIMESTAMP,
            "passed": True,
            "results": [],
        },
        "visual_review": {
            "automated_preflight_passed": True,
            "rendered_pages_generated": False,
            "automated_visual_heuristics_passed": False,
            "human_visual_review_recorded": False,
            "human_reviewer": None,
            "human_reviewed_at": None,
            "pages_reviewed": None,
        },
        "completion_gates": {
            "sources_inventoried": True,
            "outline_approved": True,
            "canonical_content_complete": True,
            "all_examples_have_records": True,
            "no_unresolved_presented_as_verified": True,
            "language_editions_in_parity": True,
            "pdf_preflight_executed": True,
            "page_counts_match_actual": True,
            "no_stale_verification_records": True,
        },
        "tool_results": [
            {"tool": "pdf_preflight.py", "status": "pass", "run_at": TIMESTAMP, "detail": None}
        ],
        "updated_at": TIMESTAMP,
    }
    state.update(overrides)
    return state


MANIFEST: dict[str, Any] = {
    "schema_version": 1,
    "generated_at": TIMESTAMP,
    "root": "sources",
    "sources": [
        {
            "source_id": "SRC-001",
            "filename": "lecture-week-01.pdf",
            "relative_path": "lecture-week-01.pdf",
            "source_class": "lecture_materials",
            "page_count": 24,
            "year": 2025,
            "title": "Steady-flow energy equation",
            "course_code": "MECH2001",
            "contains_questions": False,
            "contains_solutions": False,
            "text_extractable": True,
            "appears_scanned": False,
            "handwriting_present": False,
            "visual_inspection_required": False,
            "ocr_required": False,
            "exam_relevance": "high",
            "confidence": "high",
            "notes": None,
        },
        {
            "source_id": "SRC-002",
            "filename": "thermo-data-sheet.pdf",
            "relative_path": "thermo-data-sheet.pdf",
            "source_class": "datasheets",
            "page_count": 6,
            "year": None,
            "title": "Thermodynamics data sheet",
            "course_code": None,
            "contains_questions": False,
            "contains_solutions": False,
            "text_extractable": True,
            "appears_scanned": False,
            "handwriting_present": False,
            "visual_inspection_required": False,
            "ocr_required": False,
            "exam_relevance": "high",
            "confidence": "high",
            "notes": None,
        },
    ],
    "missing_sources": [],
}


def build_minimal_valid(dest: Path) -> Path:
    """Materialise a working directory that passes the final audit.

    Args:
        dest: Directory to create (removed first if it exists).

    Returns:
        The created directory.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    write_text(dest / "canonical-content" / f"{CHAPTER_ID}.md", CHAPTER_MARKDOWN)
    save_json(dest / "canonical-content" / f"{CHAPTER_ID}.json", CHAPTER_SIDECAR)
    write_text(dest / "editions" / "english" / f"{CHAPTER_ID}.md", EDITION_ENGLISH)
    write_text(dest / "editions" / "bilingual" / f"{CHAPTER_ID}.md", EDITION_BILINGUAL)
    save_json(dest / "source-manifest.json", MANIFEST)
    write_text(
        dest / "verification" / f"{EXAMPLE_ID}-recompute.md",
        "# Independent recomputation — WE-01-01\n\n"
        "Wdot = mdot (h1 - h2) = 2.0 kg/s * (3200 - 2500) kJ/kg = 1400 kW.\n"
        "Units: kg/s * kJ/kg = kJ/s = kW. Sign: positive out of the turbine.\n",
    )
    write_minimal_pdf(dest / "output" / "notes-en.pdf", NOTES_PDF_PAGES)

    record = _record()
    record["content_hash"]["value"] = current_block_hash(dest, EXAMPLE_ID)
    save_json(dest / "solution-records" / "REC-001.json", record)
    save_json(dest / "progress.json", _progress())
    return dest


def current_block_hash(work_dir: Path, block_id: str) -> str:
    """Hash a canonical block as it currently stands on disk.

    Args:
        work_dir: Fixture working directory.
        block_id: Anchored block ID.

    Returns:
        Hex digest of the block body.
    """
    path = work_dir / "canonical-content" / f"{CHAPTER_ID}.md"
    blocks = block_index(parse_blocks(path.read_text(encoding="utf-8")))
    return blocks[block_id].content_hash


def build_missing_evidence(dest: Path) -> Path:
    """A VERIFIED record whose evidence list is empty."""
    build_minimal_valid(dest)
    record = _record(evidence=[])
    record["content_hash"]["value"] = current_block_hash(dest, EXAMPLE_ID)
    save_json(dest / "solution-records" / "REC-001.json", record)
    return dest


def build_missing_check(dest: Path) -> Path:
    """A VERIFIED record missing a check the profile requires."""
    build_minimal_valid(dest)
    record = _record()
    record["checks"] = [
        check for check in record["checks"] if check["check_id"] != "energy_balance"
    ]
    record["content_hash"]["value"] = current_block_hash(dest, EXAMPLE_ID)
    save_json(dest / "solution-records" / "REC-001.json", record)
    return dest


def build_unresolved_as_verified(dest: Path) -> Path:
    """An unresolved example still included in the finished pack."""
    build_minimal_valid(dest)
    record = _record(status="UNRESOLVED", verified_at=None, verified_by=None)
    record["unresolved_questions"] = ["Inlet enthalpy is unreadable in the scan."]
    record["content_hash"]["value"] = current_block_hash(dest, EXAMPLE_ID)
    save_json(dest / "solution-records" / "REC-001.json", record)
    return dest


def build_stale_content(dest: Path) -> Path:
    """Canonical text edited after the record was written."""
    build_minimal_valid(dest)
    path = dest / "canonical-content" / f"{CHAPTER_ID}.md"
    edited = path.read_text(encoding="utf-8").replace("2.0 * 700 = 1400 kW", "2.5 * 700 = 1750 kW")
    write_text(path, edited)
    return dest


def build_page_count_mismatch(dest: Path) -> Path:
    """Progress reports a page count the PDF does not have."""
    build_minimal_valid(dest)
    state = _progress()
    state["artifacts"][0]["reported_page_count"] = len(NOTES_PDF_PAGES) + 40
    save_json(dest / "progress.json", state)
    return dest


def build_parity_mismatch(dest: Path) -> Path:
    """The bilingual edition drops a worked example the English edition has."""
    build_minimal_valid(dest)
    trimmed = EDITION_BILINGUAL.split(f"<!-- id: {EXAMPLE_ID}")[0] + f"<!-- end: {CHAPTER_ID} -->\n"
    write_text(dest / "editions" / "bilingual" / f"{CHAPTER_ID}.md", trimmed)
    return dest


def build_missing_approval(dest: Path) -> Path:
    """Drafting proceeded without a recorded outline approval."""
    build_minimal_valid(dest)
    state = _progress()
    state["approval"] = {
        "outline_approved": False,
        "approved_at": None,
        "approved_by": None,
        "approval_note": None,
    }
    state["completion_gates"]["outline_approved"] = False
    save_json(dest / "progress.json", state)
    return dest


def build_missing_artifact(dest: Path) -> Path:
    """Progress declares an artefact that was never produced."""
    build_minimal_valid(dest)
    (dest / "output" / "notes-en.pdf").unlink()
    return dest


def build_no_preflight(dest: Path) -> Path:
    """PDF preflight was never executed."""
    build_minimal_valid(dest)
    state = _progress()
    state["pdf_preflight"] = {"executed": False, "executed_at": None, "passed": None, "results": []}
    state["completion_gates"]["pdf_preflight_executed"] = False
    save_json(dest / "progress.json", state)
    return dest


def build_hangul_in_english(dest: Path) -> Path:
    """Korean text left in the English-only edition."""
    build_minimal_valid(dest)
    path = dest / "editions" / "english" / f"{CHAPTER_ID}.md"
    leaked = path.read_text(encoding="utf-8").replace(
        "### Worked example 1.1 — adiabatic turbine",
        "### Worked example 1.1 — adiabatic turbine (단열 터빈)",
    )
    write_text(path, leaked)
    return dest


VARIANTS: dict[str, Callable[[Path], Path]] = {
    "minimal-valid": build_minimal_valid,
    "missing-evidence": build_missing_evidence,
    "missing-check": build_missing_check,
    "unresolved-as-verified": build_unresolved_as_verified,
    "stale-content": build_stale_content,
    "page-count-mismatch": build_page_count_mismatch,
    "parity-mismatch": build_parity_mismatch,
    "missing-approval": build_missing_approval,
    "missing-artifact": build_missing_artifact,
    "no-preflight": build_no_preflight,
    "hangul-in-english": build_hangul_in_english,
}


def main(argv: list[str] | None = None) -> int:
    """Materialise a fixture from the command line."""
    parser = argparse.ArgumentParser(
        prog="fixture_builder.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="minimal-valid")
    parser.add_argument("--dest", type=Path, required=True, help="Directory to create.")
    args = parser.parse_args(argv)
    created = VARIANTS[args.variant](args.dest)
    print(f"{args.variant} fixture written to {created}")
    print(f"generated at {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
