#!/usr/bin/env python3
"""Phase 0 environment check for an exam-prep project.

Reports what is available and what is missing, without changing anything. It
never installs a package, never writes outside the working directory, and never
touches the network.

Checks: Python version, optional dependencies, source and output directories, PDF
inspection and rendering capability, whether OCR is likely to be needed, and
whether a previous run left recoverable state.

Exit codes: 0 ready, 1 a required condition is unmet, 2 usage.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    cli_main,
    load_json,
    probe_module,
    work_file,
    work_subdir,
)
from pdf_text import available_reader, can_render_pages  # noqa: E402

#: Oldest interpreter these scripts are written against.
MIN_PYTHON = (3, 9)

#: Interpreter version the scripts are developed and tested on.
RECOMMENDED_PYTHON = (3, 11)

#: Optional packages, with what each unlocks.
OPTIONAL_PACKAGES: tuple[tuple[str, str, str], ...] = (
    ("PyYAML", "yaml", "reading .yaml profiles and configs (JSON works without it)"),
    ("pymupdf", "fitz", "PDF page text, page counts and page-image rendering"),
    ("pypdf", "pypdf", "PDF page text and page counts (no rendering)"),
    ("pdfminer.six", "pdfminer.high_level", "PDF document text only"),
    ("python-docx", "docx", "generating .docx output"),
)

#: Extensions treated as candidate source material.
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".docx", ".pptx", ".md", ".txt", ".png", ".jpg", ".jpeg"}
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="doctor.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sources", type=Path, help="Directory holding the input material.")
    parser.add_argument("--output", type=Path, help="Directory where documents will be written.")
    parser.add_argument(
        "--work-dir", type=Path, help="Project working directory to check for state."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def check_python(report: Report) -> None:
    """Check the interpreter version."""
    version = sys.version_info[:3]
    report.data["python_version"] = ".".join(str(part) for part in version)
    if version[:2] < MIN_PYTHON:
        report.fail(
            f"Python {'.'.join(str(p) for p in version)} is below the minimum "
            f"{'.'.join(str(p) for p in MIN_PYTHON)}"
        )
    elif version[:2] < RECOMMENDED_PYTHON:
        report.warn(
            f"Python {'.'.join(str(p) for p in version)} works, but "
            f"{'.'.join(str(p) for p in RECOMMENDED_PYTHON)}+ is what these scripts are tested on"
        )
    else:
        report.note(f"Python {'.'.join(str(p) for p in version)}")


def check_dependencies(report: Report) -> None:
    """Probe every optional dependency and say what each absence costs."""
    installed: dict[str, str] = {}
    for distribution, module, purpose in OPTIONAL_PACKAGES:
        available, detail = probe_module(module)
        if available:
            installed[distribution] = detail or "installed"
            report.note(f"{distribution}: available{f' ({detail})' if detail else ''}")
        else:
            report.warn(f"{distribution}: not installed — {purpose} is unavailable")
    report.data["optional_packages"] = installed

    reader, detail = available_reader()
    report.data["pdf_reader"] = reader
    if reader is None:
        report.warn(
            "no PDF reader: page text cannot be extracted, so blank-page, glyph and "
            "Hangul checks on PDFs will report SKIPPED. Page counts fall back to a "
            "stdlib parser that works only on uncompressed PDFs and refuses to guess "
            "otherwise — install pymupdf for full coverage"
        )
    else:
        report.note(f"PDF inspection: {detail}")

    renderable, render_detail = can_render_pages()
    report.data["can_render_pages"] = renderable
    if renderable:
        report.note("page rendering: available")
    else:
        report.warn(f"page rendering unavailable — {render_detail}")


def check_sources(sources: Path | None, report: Report) -> None:
    """Inspect the source directory and flag likely OCR needs."""
    if sources is None:
        report.note("no --sources given; skipping source directory check")
        return
    if not sources.is_dir():
        report.fail(f"source directory does not exist: {sources}")
        return

    files = [
        path
        for path in sorted(sources.rglob("*"))
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
    ]
    report.data["source_file_count"] = len(files)
    if not files:
        report.fail(f"no recognised source files under {sources}")
        return
    report.note(f"{len(files)} candidate source file(s) under {sources}")

    images = [path for path in files if path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    if images:
        report.warn(
            f"{len(images)} image file(s) present — these need OCR or manual transcription "
            "before their content can be cited"
        )

    _check_pdf_text_layers(files, report)


def _check_pdf_text_layers(files: list[Path], report: Report) -> None:
    """Sample PDFs to see whether a text layer exists."""
    from pdf_text import extract_pdf_text  # noqa: PLC0415 - only needed here

    pdfs = [path for path in files if path.suffix.lower() == ".pdf"]
    if not pdfs:
        return
    reader, _ = available_reader()
    if reader is None:
        report.warn(f"{len(pdfs)} PDF(s) present but no reader installed — OCR need is unknown")
        return

    no_text: list[str] = []
    for path in pdfs:
        text, _ = extract_pdf_text(path)
        if text is not None and len(text.strip()) < 1:
            no_text.append(path.name)
    report.data["pdfs_without_text_layer"] = no_text
    if no_text:
        report.warn(
            f"{len(no_text)} PDF(s) have no extractable text and will need OCR or visual "
            f"reading: {', '.join(no_text[:5])}"
        )
    else:
        report.note(f"all {len(pdfs)} PDF(s) have an extractable text layer")


def check_output(output: Path | None, report: Report) -> None:
    """Check the output directory is usable and has room."""
    if output is None:
        report.note("no --output given; skipping output directory check")
        return
    if output.exists() and not output.is_dir():
        report.fail(f"output path exists but is not a directory: {output}")
        return
    parent = output if output.is_dir() else output.parent
    if not parent.exists():
        report.fail(f"output parent directory does not exist: {parent}")
        return
    free_bytes = shutil.disk_usage(parent).free
    report.data["output_free_bytes"] = free_bytes
    report.note(f"output directory usable: {output} ({free_bytes // (1024 * 1024)} MiB free)")


def check_existing_state(work_dir: Path | None, report: Report) -> None:
    """Report recoverable state from a previous run."""
    if work_dir is None:
        report.note("no --work-dir given; skipping previous-state check")
        return
    if not work_dir.is_dir():
        report.note(f"no previous state: {work_dir} does not exist yet (this is a fresh project)")
        report.data["previous_state"] = None
        return

    progress = work_file(work_dir, "progress")
    if not progress.is_file():
        report.warn(f"{work_dir} exists but has no progress.json — state may have been lost")
        report.data["previous_state"] = "work_dir_without_progress"
        return

    state = load_json(progress)
    records = work_subdir(work_dir, "solution_records")
    record_count = len(list(records.glob("*.json"))) if records.is_dir() else 0
    report.data["previous_state"] = {
        "state": state.get("state"),
        "current_phase": state.get("current_phase"),
        "records_on_disk": record_count,
    }
    report.note(
        f"previous run found: state={state.get('state')!r} phase={state.get('current_phase')!r}, "
        f"{record_count} solution record(s) on disk — resume rather than restart"
    )
    audit = work_file(work_dir, "final_audit")
    if audit.is_file():
        verdict = load_json(audit).get("verdict")
        report.note(
            f"a previous final audit exists with verdict {verdict!r} (it will be recomputed)"
        )


def handler(args: argparse.Namespace) -> int:
    """Run every environment check."""
    report = Report(check="doctor")
    check_python(report)
    check_dependencies(report)
    check_sources(args.sources, report)
    check_output(args.output, report)
    check_existing_state(args.work_dir, report)
    report.note("no packages were installed and no source file was modified")
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
