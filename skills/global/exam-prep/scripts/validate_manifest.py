#!/usr/bin/env python3
"""Validate the source manifest produced in Phase 1.

Beyond schema conformance this enforces the source policy: IDs are unique and
stable, a file may not simultaneously be classified and flagged as unreadable
without a note, and anything ambiguous must sit in `unclassified` rather than
being quietly assigned a role it may not have.

Exit codes: 0 valid, 1 invalid, 2 usage, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    cli_main,
    load_json,
    load_schema,
    validate_instance,
    work_file,
)

#: Classes whose entries are expected to contain solved answers.
SOLUTION_CLASSES: frozenset[str] = frozenset(
    {"tutorial_solutions", "official_solutions", "mark_schemes"}
)

#: Classes whose entries are expected to contain questions.
QUESTION_CLASSES: frozenset[str] = frozenset({"tutorials", "past_papers"})


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="validate_manifest.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--work-dir",
        type=Path,
        help="Project working directory; reads source-manifest.json from it.",
    )
    group.add_argument("--manifest", type=Path, help="Path to a manifest file directly.")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def check_manifest(manifest: dict[str, Any], report: Report) -> None:
    """Apply schema and source-policy checks.

    Args:
        manifest: Parsed manifest document.
        report: Report to accumulate findings into.
    """
    for error in validate_instance(manifest, load_schema("source-manifest"), "manifest"):
        report.fail(error)

    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return

    identifiers = [item.get("source_id") for item in sources if isinstance(item, dict)]
    for source_id, count in sorted(Counter(identifiers).items()):
        if count > 1 and source_id is not None:
            report.fail(
                f"source_id {source_id!r} used {count} times — IDs must be unique and stable"
            )

    class_counts: Counter[str] = Counter()
    for entry in sources:
        if not isinstance(entry, dict):
            continue
        class_counts[str(entry.get("source_class"))] += 1
        _check_entry(entry, report)

    report.data["class_counts"] = dict(sorted(class_counts.items()))
    report.data["source_count"] = len(sources)

    unclassified = class_counts.get("unclassified", 0)
    if unclassified:
        report.note(
            f"{unclassified} file(s) remain unclassified — that is a correct outcome "
            "for ambiguous material, but they contribute nothing until a human resolves them"
        )

    if not class_counts.get("past_papers"):
        report.warn("no past_papers in the manifest — Phase 2 topic analysis will be unsupported")
    if not class_counts.get("datasheets") and not class_counts.get("formula_booklets"):
        report.warn(
            "no datasheets or formula_booklets — DS/MEM/DERIVE classification cannot be "
            "grounded and every formula will have to be treated as MEM or DERIVE"
        )


def _check_entry(entry: dict[str, Any], report: Report) -> None:
    """Check one manifest entry for internally contradictory claims."""
    source_id = entry.get("source_id", "<missing id>")
    source_class = entry.get("source_class")
    notes = entry.get("notes")

    if source_class == "unclassified" and entry.get("confidence") == "high":
        report.fail(
            f"{source_id}: classified as 'unclassified' with high confidence — "
            "if the role is genuinely unknown the confidence is not high"
        )

    if source_class in SOLUTION_CLASSES and entry.get("contains_solutions") is False:
        report.fail(
            f"{source_id}: class {source_class!r} contradicts contains_solutions=false"
        )

    if source_class in QUESTION_CLASSES and entry.get("contains_questions") is False:
        report.fail(
            f"{source_id}: class {source_class!r} contradicts contains_questions=false"
        )

    text_extractable = entry.get("text_extractable")
    if text_extractable is False and not entry.get("ocr_required") and not notes:
        report.warn(
            f"{source_id}: no extractable text and OCR not flagged — record how the "
            "content will actually be read, or set ocr_required"
        )

    if entry.get("appears_scanned") and entry.get("visual_inspection_required") is None:
        report.warn(
            f"{source_id}: appears scanned but visual_inspection_required is unset"
        )

    if entry.get("handwriting_present") and text_extractable is None:
        report.warn(f"{source_id}: handwriting present but text_extractable was never determined")


def handler(args: argparse.Namespace) -> int:
    """Validate the manifest named on the command line."""
    path = args.manifest if args.manifest else work_file(args.work_dir, "manifest")
    report = Report(check="validate_manifest")
    report.note(f"manifest: {path}")
    check_manifest(load_json(path), report)
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
