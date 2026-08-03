#!/usr/bin/env python3
"""Automated preflight for a generated PDF.

Checks performed:
  * the file exists and is non-empty;
  * the PDF is readable by an installed reader;
  * the page count is read **from the file** (never from a plan or estimate);
  * the reported page count, if one is supplied, matches the real one;
  * output size per page is not suspiciously small;
  * pages with (almost) no visible text are flagged — see BLANK_PAGE_HEURISTIC;
  * replacement / missing-glyph characters are detected.

It also writes a plain-text sidecar of the extracted text so the output can be
searched, diffed and re-reviewed later without re-parsing the PDF.

Passing preflight means the file is structurally sound. It says nothing about
whether the mathematics inside it is correct, and nothing about whether a human
looked at any page.

Exit codes: 0 pass, 1 fail, 2 usage, 3 no PDF reader installed, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    cli_main,
    find_replacement_characters,
    visible_character_count,
    work_subdir,
    write_text,
)
from pdf_text import extract_pdf_pages, pdf_page_count  # noqa: E402

#: A page with fewer visible characters than this is reported as possibly blank.
#: It is a heuristic, not proof: a full-page figure or a plate legitimately has
#: almost no extractable text, so this is a warning that asks for a human look.
BLANK_PAGE_HEURISTIC = 12

#: Below this many bytes per page the file is almost certainly truncated or empty.
#: This is the substantive size check — it scales with the document.
MIN_BYTES_PER_PAGE = 400

#: Absolute floor catching stub and zero-length files. Deliberately low: a short
#: but genuine two-page document can be under 2 KiB, and the per-page floor above
#: is what actually detects truncated output.
MIN_TOTAL_BYTES = 512


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="pdf_preflight.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf", type=Path, nargs="+", help="PDF file(s) to inspect.")
    parser.add_argument(
        "--expect-pages",
        type=int,
        help="Page count previously reported. Fails when it differs from the real count.",
    )
    parser.add_argument(
        "--min-pages",
        type=int,
        help="Fail when the real page count is below this value.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Working directory; text sidecars are written to its pdf-text/ folder.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def preflight(
    path: Path,
    report: Report,
    expect_pages: int | None = None,
    min_pages: int | None = None,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Inspect one PDF and record findings.

    Args:
        path: PDF to inspect.
        report: Report to accumulate findings into.
        expect_pages: Previously reported page count to verify, if any.
        min_pages: Minimum acceptable page count, if any.
        work_dir: Working directory for the text sidecar, if any.

    Returns:
        A result record suitable for storing in progress.json.
    """
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "actual_page_count": None,
        "readable": False,
        "sidecar": None,
    }

    if not path.is_file():
        report.fail(f"{path}: file does not exist — the artefact was not produced")
        return result

    size = path.stat().st_size
    result["size_bytes"] = size
    if size < MIN_TOTAL_BYTES:
        report.fail(f"{path.name}: only {size} bytes — too small to be a real document")

    page_count, detail = pdf_page_count(path)
    if page_count is None:
        report.skipped_reason = detail
        report.warn(f"{path.name}: page count not readable — {detail}")
        return result

    result["actual_page_count"] = page_count
    result["readable"] = True
    report.note(f"{path.name}: {page_count} page(s), {size} bytes ({detail})")

    if page_count == 0:
        report.fail(f"{path.name}: reports zero pages")
    elif size / page_count < MIN_BYTES_PER_PAGE:
        report.fail(
            f"{path.name}: {size // page_count} bytes/page is below the "
            f"{MIN_BYTES_PER_PAGE} byte floor — output looks truncated or blank"
        )

    if expect_pages is not None and expect_pages != page_count:
        report.fail(
            f"{path.name}: reported page count {expect_pages} does not match the actual "
            f"{page_count} pages read from the file"
        )
    if min_pages is not None and page_count < min_pages:
        report.fail(f"{path.name}: {page_count} pages is below the required minimum {min_pages}")

    _inspect_pages(path, page_count, report, result, work_dir)
    return result


def _inspect_pages(
    path: Path,
    page_count: int,
    report: Report,
    result: dict[str, Any],
    work_dir: Path | None,
) -> None:
    """Run per-page text checks and write the text sidecar."""
    pages, detail = extract_pdf_pages(path)
    if pages is None:
        report.warn(f"{path.name}: per-page text unavailable — {detail}")
        result["page_text_available"] = False
        return

    result["page_text_available"] = True

    blank_pages = [
        number
        for number, text in enumerate(pages, start=1)
        if visible_character_count(text) < BLANK_PAGE_HEURISTIC
    ]
    if blank_pages:
        result["possibly_blank_pages"] = blank_pages
        report.warn(
            f"{path.name}: page(s) {_summarise(blank_pages)} have fewer than "
            f"{BLANK_PAGE_HEURISTIC} visible characters — possibly blank. This is a "
            "heuristic: full-page figures look the same. A human must confirm."
        )

    broken: list[str] = []
    for number, text in enumerate(pages, start=1):
        for line_no, char in find_replacement_characters(text):
            broken.append(f"page {number}, line {line_no}: {char!r}")
    if broken:
        result["replacement_characters"] = broken
        report.fail(
            f"{path.name}: {len(broken)} replacement/missing-glyph character(s) — "
            "a font failed to embed. First: " + broken[0]
        )

    if work_dir is not None:
        sidecar = work_subdir(work_dir, "pdf_text") / f"{path.stem}.txt"
        body = "\n".join(
            f"<!-- page {number} -->\n{text}" for number, text in enumerate(pages, start=1)
        )
        write_text(sidecar, body)
        result["sidecar"] = str(sidecar)
        report.note(f"{path.name}: text sidecar written to {sidecar}")


def _summarise(numbers: list[int], limit: int = 10) -> str:
    """Render a page-number list compactly."""
    if len(numbers) <= limit:
        return ", ".join(str(number) for number in numbers)
    head = ", ".join(str(number) for number in numbers[:limit])
    return f"{head} ... (+{len(numbers) - limit} more)"


def handler(args: argparse.Namespace) -> int:
    """Preflight every PDF named on the command line."""
    report = Report(check="pdf_preflight")
    if args.expect_pages is not None and len(args.pdf) > 1:
        report.fail("--expect-pages applies to a single PDF; pass one file at a time")
        return report.emit(args.as_json)

    results = [
        preflight(path, report, args.expect_pages, args.min_pages, args.work_dir)
        for path in args.pdf
    ]
    report.data["results"] = results
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
