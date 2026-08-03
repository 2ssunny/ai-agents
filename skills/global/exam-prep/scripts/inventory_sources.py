#!/usr/bin/env python3
"""Phase 1 source inventory.

Walks the source directory and produces source-manifest.json: one entry per file
with a stable ID, a proposed class, and every property that could actually be
determined from the file. Anything the filename and content do not settle is left
null, and anything genuinely ambiguous is classed `unclassified` with low
confidence rather than being assigned a role it may not have.

The classifier is a filename heuristic. It is deliberately conservative: it is
better to leave twenty files unclassified for a human to sort than to silently
treat a tutorial sheet as a past paper and build an exam analysis on it.

Existing manifests are respected: a file that already has an entry keeps its
source_id and any human-corrected fields unless --overwrite is given.

Exit codes: 0 written, 1 nothing to inventory, 2 usage, 4 unreadable directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    SkillError,
    cli_main,
    load_json,
    save_json,
    work_file,
)
from pdf_text import available_reader, extract_pdf_text, pdf_page_count  # noqa: E402

MANIFEST_SCHEMA_VERSION = 1

#: Extensions inventoried.
INVENTORY_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".docx", ".pptx", ".md", ".txt", ".png", ".jpg", ".jpeg"}
)

#: Marker -> weight, per source class. Matching is on the lower-cased relative path.
CLASS_MARKERS: dict[str, tuple[tuple[str, int], ...]] = {
    "official_solutions": (("official solution", 3), ("model answer", 3), ("examiner", 2)),
    "mark_schemes": (("mark scheme", 3), ("markscheme", 3), ("marking scheme", 3)),
    "tutorial_solutions": (("tutorial solution", 3), ("sheet solution", 3),
                           ("problem set solution", 3)),
    "past_papers": (("past paper", 3), ("past exam", 3), ("exam paper", 3), ("examination", 2)),
    "tutorials": (("tutorial", 2), ("problem sheet", 3), ("problem set", 3), ("exercise", 2),
                  ("worksheet", 2), ("homework", 2)),
    "lecture_materials": (("lecture", 3), ("slide", 2), ("handout", 2), ("week", 1)),
    "textbooks": (("textbook", 3), ("chapter", 1)),
    "datasheets": (("data sheet", 3), ("datasheet", 3), ("data book", 3), ("databook", 3)),
    "formula_booklets": (("formula", 3), ("formulae", 3), ("equation sheet", 3)),
    "scope_guidance": (("syllabus", 3), ("scope", 2), ("revision guide", 3), ("exam info", 3),
                       ("learning outcome", 3)),
    "reference_notes": (("summary", 2), ("cheat sheet", 3), ("reference", 2), ("revision note", 3)),
}

#: Words indicating the document contains solved answers.
SOLUTION_MARKERS: tuple[str, ...] = ("solution", "soln", "answer", "worked", "model")

#: Minimum score before a class is proposed at all.
MIN_SCORE = 2

#: Score gap below which two candidate classes are treated as ambiguous.
AMBIGUITY_MARGIN = 1

YEAR_RE = re.compile(r"(?:^|[^0-9])(19[89][0-9]|20[0-4][0-9])(?:[^0-9]|$)")
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4}[ _-]?\d{3,5})\b")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="inventory_sources.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sources", type=Path, required=True, help="Directory of input material.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Project working directory; source-manifest.json is written here.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rebuild every entry, discarding human corrections in the existing manifest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def classify(relative_path: str) -> tuple[str, str, str | None]:
    """Propose a source class from a path.

    Args:
        relative_path: Path of the file relative to the source root.

    Returns:
        ``(source_class, confidence, note)``. Ambiguous input yields
        ``("unclassified", "low", reason)``.
    """
    text = relative_path.lower().replace("_", " ").replace("-", " ")
    scores: dict[str, int] = {}
    for source_class, markers in CLASS_MARKERS.items():
        score = sum(weight for marker, weight in markers if marker in text)
        if score:
            scores[source_class] = score

    if not scores:
        return "unclassified", "low", "no filename marker matched any source class"

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best_class, best_score = ranked[0]

    if best_score < MIN_SCORE:
        return "unclassified", "low", f"weak signal only (best: {best_class}, score {best_score})"

    if len(ranked) > 1 and best_score - ranked[1][1] <= AMBIGUITY_MARGIN:
        competitors = ", ".join(f"{name}({score})" for name, score in ranked[:3])
        return "unclassified", "low", f"ambiguous between {competitors}"

    # A questions document that also mentions solutions is a solutions document.
    has_solution_marker = any(marker in text for marker in SOLUTION_MARKERS)
    if has_solution_marker:
        if best_class == "tutorials":
            return "tutorial_solutions", "medium", "tutorial filename also mentions solutions"
        if best_class == "past_papers":
            return "official_solutions", "medium", "past-paper filename also mentions solutions"

    confidence = "high" if best_score >= MIN_SCORE + AMBIGUITY_MARGIN else "medium"
    return best_class, confidence, None


def inspect_file(path: Path, source_class: str) -> dict[str, Any]:
    """Determine what can actually be read from a file.

    Args:
        path: File to inspect.
        source_class: Proposed class, used only for question/solution expectations.

    Returns:
        Partial manifest entry; unknown values are None, never guessed.
    """
    facts: dict[str, Any] = {
        "page_count": None,
        "text_extractable": None,
        "appears_scanned": None,
        "handwriting_present": None,
        "visual_inspection_required": None,
        "ocr_required": None,
        "contains_questions": None,
        "contains_solutions": None,
    }

    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        facts.update(
            {
                "text_extractable": False,
                "appears_scanned": True,
                "visual_inspection_required": True,
                "ocr_required": True,
            }
        )
        return facts

    if path.suffix.lower() != ".pdf":
        return facts

    reader, _ = available_reader()
    if reader is None:
        return facts

    pages, _ = pdf_page_count(path)
    facts["page_count"] = pages

    text, _ = extract_pdf_text(path)
    if text is None:
        return facts

    stripped = text.strip()
    facts["text_extractable"] = bool(stripped)
    if not stripped:
        facts.update(
            {"appears_scanned": True, "ocr_required": True, "visual_inspection_required": True}
        )
        return facts

    lowered = stripped.lower()
    if source_class in {"tutorials", "past_papers"}:
        facts["contains_questions"] = True
    if any(marker in lowered for marker in ("solution", "answer:", "model answer")):
        facts["contains_solutions"] = True

    return facts


def build_entry(path: Path, root: Path, source_id: str) -> dict[str, Any]:
    """Build one manifest entry for a file.

    Args:
        path: File to describe.
        root: Source root, used for the relative path.
        source_id: Stable ID to assign.

    Returns:
        A manifest entry.
    """
    relative = path.relative_to(root).as_posix()
    source_class, confidence, note = classify(relative)
    entry: dict[str, Any] = {
        "source_id": source_id,
        "filename": path.name,
        "relative_path": relative,
        "source_class": source_class,
        "confidence": confidence,
        "notes": note,
        "title": None,
        "course_code": None,
        "year": None,
        "exam_relevance": "unknown",
    }
    entry.update(inspect_file(path, source_class))

    year_match = YEAR_RE.search(relative)
    if year_match:
        entry["year"] = int(year_match.group(1))
    code_match = COURSE_CODE_RE.search(path.name.upper())
    if code_match:
        entry["course_code"] = code_match.group(1)

    return entry


def handler(args: argparse.Namespace) -> int:
    """Build (or refresh) the source manifest."""
    report = Report(check="inventory_sources")
    if not args.sources.is_dir():
        raise SkillError(f"source directory not found: {args.sources}", 4)

    files = [
        path
        for path in sorted(args.sources.rglob("*"))
        if path.is_file() and path.suffix.lower() in INVENTORY_EXTENSIONS
    ]
    if not files:
        report.fail(f"no recognised source files under {args.sources}")
        return report.emit(args.as_json)

    manifest_path = work_file(args.work_dir, "manifest")
    existing: dict[str, dict[str, Any]] = {}
    next_number = 1
    if manifest_path.is_file() and not args.overwrite:
        previous = load_json(manifest_path)
        for entry in previous.get("sources") or []:
            key = entry.get("relative_path") or entry.get("filename")
            existing[str(key)] = entry
            number = int(str(entry.get("source_id", "SRC-000")).split("-")[-1])
            next_number = max(next_number, number + 1)

    entries: list[dict[str, Any]] = []
    reused = 0
    for path in files:
        relative = path.relative_to(args.sources).as_posix()
        if relative in existing:
            entries.append(existing[relative])
            reused += 1
            continue
        entries.append(build_entry(path, args.sources, f"SRC-{next_number:03d}"))
        next_number += 1

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "root": str(args.sources),
        "sources": entries,
        "missing_sources": (
            load_json(manifest_path).get("missing_sources", [])
            if manifest_path.is_file() and not args.overwrite
            else []
        ),
    }

    unclassified = [entry for entry in entries if entry["source_class"] == "unclassified"]
    report.note(f"{len(entries)} file(s) inventoried ({reused} kept from the existing manifest)")
    if unclassified:
        report.warn(
            f"{len(unclassified)} file(s) left unclassified — classify them by hand before "
            f"Phase 2: {', '.join(entry['filename'] for entry in unclassified[:5])}"
        )
    if available_reader()[0] is None:
        report.warn(
            "no PDF reader installed: page counts, text-layer and OCR flags were left null "
            "rather than guessed"
        )

    report.data["entries"] = len(entries)
    report.data["unclassified"] = len(unclassified)

    if args.dry_run:
        report.note(f"dry run — {manifest_path} was not written")
    else:
        save_json(manifest_path, manifest)
        report.note(f"written to {manifest_path}")

    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
