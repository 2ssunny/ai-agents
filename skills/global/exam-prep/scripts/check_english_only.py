#!/usr/bin/env python3
"""Detect Hangul left in an English-only artefact.

The English edition is produced from the same canonical model as the bilingual
one, so Korean text leaks in through copy-paste and half-translated blocks. This
finds every Hangul run and reports its location so it can be fixed in the text
source rather than patched in the rendered output.

Works on Markdown/text sources directly, and on PDFs when a reader is installed
(otherwise the PDF is reported as SKIPPED, never as passing).

Exit codes: 0 clean, 1 Hangul found, 2 usage, 3 no PDF reader, 4 unreadable input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    SkillError,
    cli_main,
    hangul_positions,
    read_text,
)
from pdf_text import extract_pdf_text  # noqa: E402

TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".txt", ".tex", ".html", ".json"})

#: Default cap on reported occurrences so a badly wrong file stays readable.
DEFAULT_MAX_REPORTED = 40


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="check_english_only.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=Path,
        nargs="+",
        help="Files or directories to scan (.md/.txt/.tex/.html/.json and .pdf).",
    )
    parser.add_argument(
        "--max-reported",
        type=int,
        default=DEFAULT_MAX_REPORTED,
        help=f"Maximum occurrences to list per file (default: {DEFAULT_MAX_REPORTED}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def iter_targets(targets: list[Path]) -> list[Path]:
    """Expand directories into the scannable files they contain.

    Args:
        targets: Files and/or directories from the command line.

    Returns:
        Sorted list of files to scan.

    Raises:
        SkillError: If a named path does not exist.
    """
    scannable = TEXT_SUFFIXES | {".pdf"}
    files: list[Path] = []
    for target in targets:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(
                path
                for path in sorted(target.rglob("*"))
                if path.is_file() and path.suffix.lower() in scannable
            )
        else:
            raise SkillError(f"no such file or directory: {target}", 4)
    return files


def scan_file(path: Path, max_reported: int, report: Report) -> None:
    """Scan one file and record any Hangul found.

    Args:
        path: File to scan.
        max_reported: Maximum occurrences to list for this file.
        report: Report to accumulate findings into.
    """
    if path.suffix.lower() == ".pdf":
        text, detail = extract_pdf_text(path)
        if text is None:
            report.warn(f"{path.name}: not scanned — {detail}")
            report.data.setdefault("skipped_files", []).append(str(path))
            return
    else:
        text = read_text(path)

    occurrences = hangul_positions(text)
    if not occurrences:
        report.note(f"{path.name}: no Hangul")
        return

    report.fail(f"{path.name}: {len(occurrences)} Hangul occurrence(s) in an English-only artefact")
    for line_no, column, run in occurrences[:max_reported]:
        report.fail(f"  {path.name}:{line_no}:{column}: {run!r}")
    if len(occurrences) > max_reported:
        report.fail(f"  {path.name}: ... {len(occurrences) - max_reported} more not listed")


def handler(args: argparse.Namespace) -> int:
    """Scan every named target."""
    report = Report(check="check_english_only")
    files = iter_targets(args.target)
    if not files:
        raise SkillError("no scannable files found in the given targets", 4)
    for path in files:
        scan_file(path, args.max_reported, report)
    report.data["files_scanned"] = len(files)
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
