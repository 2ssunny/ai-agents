#!/usr/bin/env python3
"""Render PDF pages to images and build a contact sheet for human review.

Rendering requires PyMuPDF. When it is absent the command reports SKIPPED and
exits 3 — it never pretends the pages were produced.

The contact sheet is a plain HTML file referencing the rendered PNGs, so it needs
no image-processing dependency and stays a text artefact that can be opened in any
browser and kept under version control alongside the rest of the work.

IMPORTANT: generating a contact sheet is not visual inspection. It only makes
inspection possible. Human review is recorded separately with
`record_human_review.py`, and only a person may record it.

Exit codes: 0 rendered, 1 failure, 2 usage, 3 PyMuPDF not installed, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    SkillError,
    cli_main,
    work_subdir,
    write_text,
)
from pdf_text import can_render_pages  # noqa: E402

#: Rendering resolution. 96 dpi is legible in a contact sheet without huge files.
DEFAULT_DPI = 96

#: Thumbnail width in the contact sheet, in CSS pixels.
THUMBNAIL_WIDTH_PX = 220


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="render_contact_sheet.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf", type=Path, help="PDF to render.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Working directory; pages are written under its rendered-pages/ folder.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Render resolution in dpi (default: {DEFAULT_DPI}).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Render only the first N pages (useful for a quick look at a long document).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def render(pdf: Path, out_dir: Path, dpi: int, max_pages: int | None) -> list[Path]:
    """Render PDF pages to PNG files.

    Args:
        pdf: PDF to render.
        out_dir: Destination directory (created if missing).
        dpi: Render resolution.
        max_pages: Optional cap on the number of pages rendered.

    Returns:
        Paths of the written PNG files, in page order.

    Raises:
        SkillError: If PyMuPDF is missing or the PDF cannot be rendered.
    """
    try:
        import fitz  # noqa: PLC0415 - optional dependency
    except ImportError as exc:
        raise SkillError(
            "page rendering needs PyMuPDF (`pip install pymupdf` in your project "
            "environment). No pages were rendered.",
            3,
        ) from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    try:
        with fitz.open(pdf) as document:
            total = document.page_count
            limit = total if max_pages is None else min(max_pages, total)
            for index in range(limit):
                pixmap = document.load_page(index).get_pixmap(dpi=dpi)
                target = out_dir / f"page-{index + 1:04d}.png"
                pixmap.save(target)
                written.append(target)
    except SkillError:
        raise
    except Exception as exc:  # noqa: BLE001 - broken PDFs must not crash the run
        raise SkillError(f"rendering {pdf.name} failed: {type(exc).__name__}: {exc}", 1) from exc
    return written


def build_contact_sheet(pdf: Path, pages: list[Path], destination: Path) -> None:
    """Write an HTML contact sheet referencing the rendered pages.

    Args:
        pdf: Source PDF (named in the heading).
        pages: Rendered page images, in order.
        destination: HTML file to write.
    """
    cells = "\n".join(
        f'  <figure><img src="{html.escape(page.name)}" alt="page {index}">'
        f"<figcaption>p.{index}</figcaption></figure>"
        for index, page in enumerate(pages, start=1)
    )
    document = f"""<!doctype html>
<meta charset="utf-8">
<title>Contact sheet — {html.escape(pdf.name)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 1.5rem; }}
  .warning {{ border: 1px solid currentColor; padding: 0.75rem; margin-bottom: 1rem; }}
  .sheet {{ display: flex; flex-wrap: wrap; gap: 0.75rem; }}
  figure {{ margin: 0; width: {THUMBNAIL_WIDTH_PX}px; }}
  img {{ width: 100%; height: auto; border: 1px solid #8888; }}
  figcaption {{ font-size: 0.8rem; text-align: center; }}
</style>
<h1>Contact sheet — {html.escape(pdf.name)}</h1>
<p class="warning"><strong>This sheet is not a review.</strong> It exists so a human
can look at {len(pages)} rendered page(s). Until a person records their review, the
pages count as rendered and automatically checked only.</p>
<div class="sheet">
{cells}
</div>
"""
    write_text(destination, document)


def handler(args: argparse.Namespace) -> int:
    """Render the PDF and build its contact sheet."""
    report = Report(check="render_contact_sheet")

    available, detail = can_render_pages()
    if not available:
        report.skipped_reason = detail
        report.warn("no pages were rendered; do not claim visual inspection")
        return report.emit(args.as_json)

    if not args.pdf.is_file():
        raise SkillError(f"no such file: {args.pdf}", 4)

    out_dir = work_subdir(args.work_dir, "rendered_pages") / args.pdf.stem
    pages = render(args.pdf, out_dir, args.dpi, args.max_pages)
    if not pages:
        report.fail(f"{args.pdf.name}: no pages were rendered")
        return report.emit(args.as_json)

    sheet = out_dir / "contact-sheet.html"
    build_contact_sheet(args.pdf, pages, sheet)

    report.note(f"rendered {len(pages)} page(s) to {out_dir}")
    report.note(f"contact sheet: {sheet}")
    report.note(
        "rendered_pages_generated=true may now be set. "
        "human_visual_review_recorded stays false until a person records it."
    )
    report.data["page_images"] = len(pages)
    report.data["contact_sheet"] = str(sheet)
    report.data["output_dir"] = str(out_dir)
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
