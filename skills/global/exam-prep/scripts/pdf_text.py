"""PDF reading helpers with graceful degradation.

Every function returns ``(value, detail)`` where a ``None`` value means the PDF
could not be read and ``detail`` explains why. Callers must surface that as
SKIPPED — never as a passing check. A PDF that could not be inspected has not
been inspected.

Readers are tried in order of fidelity: PyMuPDF (per-page text and rendering),
pypdf (per-page text, no rendering), pdfminer.six (whole-document text only).
All are optional dependencies; nothing here reaches the network.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Human-readable install hint reused across scripts.
INSTALL_HINT = (
    "install one of: pymupdf (best: page text + rendering), pypdf (page text), "
    "pdfminer.six (document text) — e.g. `pip install pymupdf` in your project environment"
)


def _import_reader() -> tuple[str | None, object | None]:
    """Import the highest-fidelity PDF reader available.

    Returns:
        ``(reader_name, module)``; ``(None, None)`` when nothing is installed.
    """
    try:
        import fitz  # noqa: PLC0415 - optional dependency

        return "pymupdf", fitz
    except ImportError:
        pass
    try:
        import pypdf  # noqa: PLC0415 - optional dependency

        return "pypdf", pypdf
    except ImportError:
        pass
    try:
        from pdfminer import high_level  # noqa: PLC0415 - optional dependency

        return "pdfminer.six", high_level
    except ImportError:
        pass
    return None, None


def available_reader() -> tuple[str | None, str]:
    """Report which PDF reader will be used.

    Returns:
        ``(reader_name, detail)``; name is None when no reader is installed.
    """
    name, _ = _import_reader()
    if name is None:
        return None, f"no PDF reader installed — {INSTALL_HINT}"
    return name, f"using {name}"


def extract_pdf_pages(path: Path) -> tuple[list[str] | None, str]:
    """Extract text page by page.

    Args:
        path: PDF file.

    Returns:
        ``(pages, detail)``. ``pages`` is None when the file could not be read
        page-wise; pdfminer.six cannot split pages here and returns None with an
        explanatory detail.
    """
    if not path.is_file():
        return None, f"file not found: {path}"

    name, module = _import_reader()
    if name is None:
        return None, f"no PDF reader installed — {INSTALL_HINT}"

    try:
        if name == "pymupdf":
            with module.open(path) as document:  # type: ignore[union-attr]
                return [page.get_text() for page in document], f"read with {name}"
        if name == "pypdf":
            reader = module.PdfReader(str(path))  # type: ignore[union-attr]
            return [(page.extract_text() or "") for page in reader.pages], f"read with {name}"
    except Exception as exc:  # noqa: BLE001 - a broken PDF must degrade, not crash
        return None, f"{name} failed to read {path.name}: {type(exc).__name__}: {exc}"

    return None, (
        f"{name} cannot split text per page; install pymupdf or pypdf for page-level checks"
    )


def extract_pdf_text(path: Path) -> tuple[str | None, str]:
    """Extract the full text of a PDF.

    Args:
        path: PDF file.

    Returns:
        ``(text, detail)``; text is None when the file could not be read.
    """
    pages, detail = extract_pdf_pages(path)
    if pages is not None:
        return "\n".join(pages), detail

    name, module = _import_reader()
    if name == "pdfminer.six":
        try:
            return module.extract_text(str(path)), f"read with {name}"  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 - a broken PDF must degrade, not crash
            return None, f"{name} failed to read {path.name}: {type(exc).__name__}: {exc}"
    return None, detail


_PAGES_COUNT_RE = re.compile(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", re.DOTALL)
_COUNT_PAGES_RE = re.compile(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", re.DOTALL)
_PAGE_OBJECT_RE = re.compile(rb"/Type\s*/Page(?![s])")


def stdlib_page_count(path: Path) -> tuple[int | None, str]:
    """Count pages without any third-party package.

    Two independent signals are read from the raw file: the ``/Count`` entry of
    the page tree, and the number of ``/Type /Page`` objects. A count is returned
    only when both agree, so a compressed or object-stream PDF — where neither
    pattern is reliable — yields None instead of a plausible-looking wrong number.

    Args:
        path: PDF file.

    Returns:
        ``(page_count, detail)``; count is None when the two signals disagree or
        either is absent.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"cannot read {path.name}: {exc}"

    counts = [int(match) for match in _PAGES_COUNT_RE.findall(raw)]
    counts += [int(match) for match in _COUNT_PAGES_RE.findall(raw)]
    objects = len(_PAGE_OBJECT_RE.findall(raw))

    if not counts or objects == 0:
        return None, (
            "stdlib fallback could not read the page tree (the PDF is probably "
            f"compressed or uses object streams) — {INSTALL_HINT}"
        )

    declared = max(counts)
    if declared != objects:
        return None, (
            f"stdlib fallback found /Count {declared} but {objects} page object(s); "
            f"refusing to guess — {INSTALL_HINT}"
        )
    return declared, "read with the stdlib fallback (uncompressed page tree)"


def pdf_page_count(path: Path) -> tuple[int | None, str]:
    """Read the page count from the file itself.

    The page count must always come from here, never from a plan, an estimate, or
    a previously reported number.

    Args:
        path: PDF file.

    Returns:
        ``(page_count, detail)``; count is None when the file could not be read.
    """
    if not path.is_file():
        return None, f"file not found: {path}"

    name, module = _import_reader()
    if name is None:
        return stdlib_page_count(path)

    try:
        if name == "pymupdf":
            with module.open(path) as document:  # type: ignore[union-attr]
                return document.page_count, f"read with {name}"
        if name == "pypdf":
            reader = module.PdfReader(str(path))  # type: ignore[union-attr]
            return len(reader.pages), f"read with {name}"
        pages, detail = extract_pdf_pages(path)
        if pages is None:
            return None, detail
        return len(pages), detail
    except Exception as exc:  # noqa: BLE001 - a broken PDF must degrade, not crash
        return None, f"{name} failed to read {path.name}: {type(exc).__name__}: {exc}"


def can_render_pages() -> tuple[bool, str]:
    """Report whether page images can be rendered.

    Returns:
        ``(available, detail)``.
    """
    try:
        import fitz  # noqa: PLC0415, F401 - probing availability only
    except ImportError:
        return False, "page rendering needs pymupdf (`pip install pymupdf`)"
    return True, "pymupdf available"
