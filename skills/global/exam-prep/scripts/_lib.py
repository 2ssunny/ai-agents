"""Shared helpers for the exam-prep skill scripts.

Standard library only. Optional third-party packages (PyYAML, PDF readers) are
imported lazily so that every script keeps working — with an explicit SKIPPED
result — when they are absent.

Design rules enforced here:
  * All persisted state is plain text (JSON / Markdown) with stable key order so
    that a human can edit it and ``git diff`` stays readable.
  * Nothing in this module performs network access.
  * Nothing in this module writes to the caller's source material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# --------------------------------------------------------------------------
# Exit codes
# --------------------------------------------------------------------------

EXIT_OK = 0
"""Everything the script was asked to check passed."""

EXIT_CHECK_FAILED = 1
"""The script ran correctly but the thing it inspected is not acceptable."""

EXIT_USAGE = 2
"""Bad command line (argparse also uses 2)."""

EXIT_UNAVAILABLE = 3
"""A required optional dependency or capability is missing; result is SKIPPED."""

EXIT_IO = 4
"""A path could not be read or written."""


# --------------------------------------------------------------------------
# Domain vocabulary
# --------------------------------------------------------------------------

SOURCE_CLASSES: tuple[str, ...] = (
    "lecture_materials",
    "tutorials",
    "tutorial_solutions",
    "textbooks",
    "datasheets",
    "formula_booklets",
    "past_papers",
    "official_solutions",
    "mark_schemes",
    "scope_guidance",
    "reference_notes",
    "unclassified",
)

VERIFICATION_STATUSES: tuple[str, ...] = (
    "VERIFIED",
    "VERIFIED_WITH_ROUNDING_DIFFERENCE",
    "ASSUMPTION_SENSITIVE",
    "OFFICIAL_SOLUTION_CORRECTED",
    "INSUFFICIENT_INFORMATION",
    "UNRESOLVED",
    "NOT_YET_VERIFIED",
)

#: Statuses that may be presented to the learner as a checked solution.
SETTLED_STATUSES: frozenset[str] = frozenset(
    {
        "VERIFIED",
        "VERIFIED_WITH_ROUNDING_DIFFERENCE",
        "OFFICIAL_SOLUTION_CORRECTED",
    }
)

#: Statuses that must never be described as verified in any output document.
UNRESOLVED_STATUSES: frozenset[str] = frozenset(
    {
        "ASSUMPTION_SENSITIVE",
        "INSUFFICIENT_INFORMATION",
        "UNRESOLVED",
        "NOT_YET_VERIFIED",
    }
)

#: Statuses whose records must carry full check + evidence coverage.
EVIDENCE_REQUIRED_STATUSES: frozenset[str] = frozenset(
    {
        "VERIFIED",
        "VERIFIED_WITH_ROUNDING_DIFFERENCE",
        "OFFICIAL_SOLUTION_CORRECTED",
    }
)

PROGRESS_STATES: tuple[str, ...] = (
    "not_started",
    "in_progress",
    "waiting_for_approval",
    "blocked",
    "audit_failed",
    "complete",
)

PHASES: tuple[str, ...] = (
    "phase0_environment",
    "phase1_inventory",
    "phase2_scope",
    "phase3_canonical_content",
    "phase4_verification",
    "phase5_generation",
    "phase6_checkpoint",
    "phase7_qa",
)

FORMULA_CLASSES: tuple[str, ...] = ("DS", "MEM", "DERIVE")

CANONICAL_BLOCK_KINDS: tuple[str, ...] = (
    "chapter",
    "section",
    "concept",
    "formula",
    "derivation",
    "figure",
    "worked_example",
    "past_paper_reference",
    "marking_point",
    "common_error",
)

HASH_ALGORITHM = "sha256"

#: Characters that indicate a broken glyph or failed font substitution in a PDF.
REPLACEMENT_CHARACTERS: tuple[str, ...] = ("�", "□")

_HANGUL_RANGES: tuple[tuple[int, int], ...] = (
    (0x1100, 0x11FF),  # Jamo
    (0x3130, 0x318F),  # Compatibility jamo
    (0xA960, 0xA97F),  # Jamo Extended-A
    (0xAC00, 0xD7A3),  # Syllables
    (0xD7B0, 0xD7FF),  # Jamo Extended-B
)


# --------------------------------------------------------------------------
# Text-first persistence
# --------------------------------------------------------------------------


def read_text(path: Path) -> str:
    """Read a UTF-8 text file.

    Args:
        path: File to read.

    Returns:
        Decoded file contents.

    Raises:
        SkillError: If the file cannot be read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillError(f"cannot read {path}: {exc}", EXIT_IO) from exc
    except UnicodeDecodeError as exc:
        raise SkillError(f"{path} is not valid UTF-8 text: {exc}", EXIT_IO) from exc


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, creating parent directories and ensuring a final newline.

    Args:
        path: Destination file.
        text: Content to write.

    Raises:
        SkillError: If the file cannot be written.
    """
    if not text.endswith("\n"):
        text += "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise SkillError(f"cannot write {path}: {exc}", EXIT_IO) from exc


def load_json(path: Path) -> Any:
    """Load a JSON document with an actionable error message.

    Args:
        path: JSON file to read.

    Returns:
        Parsed JSON value.

    Raises:
        SkillError: If the file is missing or malformed.
    """
    if not path.is_file():
        raise SkillError(f"missing JSON file: {path}", EXIT_IO)
    raw = read_text(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SkillError(
            f"{path} is not valid JSON (line {exc.lineno}): {exc.msg}", EXIT_IO
        ) from exc


def dump_json(value: Any) -> str:
    """Serialise a value as canonical, diff-friendly JSON text.

    Keys are sorted and indentation is fixed so that hand edits and regenerated
    files produce minimal diffs.

    Args:
        value: JSON-serialisable value.

    Returns:
        JSON text ending with a newline.
    """
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def save_json(path: Path, value: Any) -> None:
    """Write a value as canonical JSON text.

    Args:
        path: Destination file.
        value: JSON-serialisable value.
    """
    write_text(path, dump_json(value))


def load_yaml(path: Path) -> Any:
    """Load a YAML document, or a JSON document if the suffix says so.

    PyYAML is an optional dependency. When it is unavailable the caller gets a
    SkillError with EXIT_UNAVAILABLE and a concrete install hint rather than a
    bare ImportError.

    Args:
        path: YAML (or JSON) file to read.

    Returns:
        Parsed value.

    Raises:
        SkillError: If the file is missing, PyYAML is absent, or parsing fails.
    """
    if not path.is_file():
        raise SkillError(f"missing config file: {path}", EXIT_IO)
    if path.suffix.lower() == ".json":
        return load_json(path)
    try:
        import yaml  # noqa: PLC0415 - optional dependency, imported lazily
    except ImportError as exc:
        raise SkillError(
            f"reading {path.name} needs PyYAML, which is not installed.\n"
            "  Install it inside your project environment "
            "(e.g. `conda install pyyaml` or `pip install pyyaml`),\n"
            "  or supply the same document as .json instead.",
            EXIT_UNAVAILABLE,
        ) from exc
    try:
        return yaml.safe_load(read_text(path))
    except yaml.YAMLError as exc:
        raise SkillError(f"{path} is not valid YAML: {exc}", EXIT_IO) from exc


def sha256_text(text: str) -> str:
    """Hash text after newline normalisation so CRLF/LF edits do not churn hashes.

    Args:
        text: Text to hash.

    Returns:
        Lowercase hexadecimal digest.
    """
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Canonical content blocks
# --------------------------------------------------------------------------

BLOCK_START_RE = re.compile(
    r"^\s*<!--\s*id:\s*(?P<id>[A-Za-z0-9._:-]+)\s+kind:\s*(?P<kind>[a-z_]+)\s*-->\s*$"
)
BLOCK_END_RE = re.compile(r"^\s*<!--\s*end:\s*(?P<id>[A-Za-z0-9._:-]+)\s*-->\s*$")


@dataclass
class Block:
    """One identified region of a canonical-content Markdown file."""

    block_id: str
    kind: str
    body: str
    parent_id: str | None
    line_start: int
    line_end: int

    @property
    def content_hash(self) -> str:
        """sha256 of the block body, used for staleness detection."""
        return sha256_text(self.body)


def parse_blocks(text: str) -> list[Block]:
    """Extract ID-anchored blocks from canonical Markdown.

    Canonical content marks every stable identifier with HTML comments so the
    file stays a plain, hand-editable Markdown document::

        <!-- id: WE-01-02 kind: worked_example -->
        ...
        <!-- end: WE-01-02 -->

    Args:
        text: Markdown source.

    Returns:
        Blocks in document order (outer blocks appear before inner ones).

    Raises:
        SkillError: On unbalanced or mismatched markers.
    """
    lines = text.splitlines()
    open_stack: list[tuple[str, str, int, str | None]] = []
    blocks: list[Block] = []
    order: dict[str, int] = {}

    for index, line in enumerate(lines, start=1):
        start = BLOCK_START_RE.match(line)
        if start:
            block_id = start.group("id")
            if block_id in order:
                raise SkillError(
                    f"duplicate block id {block_id!r} at line {index}", EXIT_CHECK_FAILED
                )
            parent = open_stack[-1][0] if open_stack else None
            order[block_id] = len(order)
            open_stack.append((block_id, start.group("kind"), index, parent))
            continue

        end = BLOCK_END_RE.match(line)
        if end:
            block_id = end.group("id")
            if not open_stack:
                raise SkillError(
                    f"stray end marker for {block_id!r} at line {index}", EXIT_CHECK_FAILED
                )
            open_id, kind, line_start, parent = open_stack.pop()
            if open_id != block_id:
                raise SkillError(
                    f"block {open_id!r} (line {line_start}) closed by {block_id!r} at line {index}",
                    EXIT_CHECK_FAILED,
                )
            body = "\n".join(lines[line_start:index - 1])
            blocks.append(Block(open_id, kind, body, parent, line_start, index))

    if open_stack:
        unclosed = ", ".join(f"{bid!r} (line {ln})" for bid, _, ln, _ in open_stack)
        raise SkillError(f"unclosed canonical block(s): {unclosed}", EXIT_CHECK_FAILED)

    blocks.sort(key=lambda block: order[block.block_id])
    return blocks


def block_index(blocks: Iterable[Block]) -> dict[str, Block]:
    """Index blocks by their ID.

    Args:
        blocks: Blocks to index.

    Returns:
        Mapping of block ID to block.
    """
    return {block.block_id: block for block in blocks}


def contains_hangul(text: str) -> bool:
    """Report whether any Hangul code point is present.

    Args:
        text: Text to inspect.

    Returns:
        True if at least one Hangul character occurs.
    """
    return any(_is_hangul(char) for char in text)


def hangul_positions(text: str) -> list[tuple[int, int, str]]:
    """Locate every Hangul run in text.

    Args:
        text: Text to inspect.

    Returns:
        List of ``(line_number, column, run)`` tuples, 1-indexed.
    """
    found: list[tuple[int, int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        run_start: int | None = None
        for column, char in enumerate(line, start=1):
            if _is_hangul(char):
                if run_start is None:
                    run_start = column
            elif run_start is not None:
                found.append((line_no, run_start, line[run_start - 1:column - 1]))
                run_start = None
        if run_start is not None:
            found.append((line_no, run_start, line[run_start - 1:]))
    return found


def _is_hangul(char: str) -> bool:
    """Return True when a character lies in a Hangul Unicode block."""
    code = ord(char)
    return any(low <= code <= high for low, high in _HANGUL_RANGES)


def find_replacement_characters(text: str) -> list[tuple[int, str]]:
    """Locate replacement / missing-glyph characters.

    Args:
        text: Text to inspect.

    Returns:
        List of ``(line_number, character)`` tuples, 1-indexed.
    """
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for char in REPLACEMENT_CHARACTERS:
            if char in line:
                hits.append((line_no, char))
    return hits


def visible_character_count(text: str) -> int:
    """Count characters that would actually mark a page.

    Whitespace and Unicode format/control characters are ignored, so a page
    containing only spacing artefacts counts as blank.

    Args:
        text: Text to measure.

    Returns:
        Number of visible characters.
    """
    return sum(
        1
        for char in text
        if not char.isspace() and unicodedata.category(char) not in {"Cc", "Cf", "Zs", "Zl", "Zp"}
    )


# --------------------------------------------------------------------------
# Minimal JSON Schema validation (stdlib only)
# --------------------------------------------------------------------------

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def validate_instance(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate a value against a supported subset of JSON Schema.

    Supported keywords: ``type``, ``enum``, ``const``, ``required``,
    ``properties``, ``additionalProperties``, ``items``, ``minItems``,
    ``uniqueItems``, ``minimum``, ``maximum``, ``minLength``, ``pattern``,
    ``anyOf``, ``allOf``. Unsupported keywords are ignored rather than silently
    treated as satisfied checks — the schemas shipped with this skill only use
    the subset above.

    Args:
        instance: Value to validate.
        schema: Schema to validate against.
        path: JSON-path-ish prefix used in messages.

    Returns:
        A list of human-readable error strings; empty means valid.
    """
    errors: list[str] = []

    expected = schema.get("type")
    if expected is not None and not _matches_type(instance, expected):
        got = type(instance).__name__
        return [f"{path}: expected type {expected}, got {got}"]

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")

    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(item) for item in schema["enum"])
        errors.append(f"{path}: {instance!r} is not one of [{allowed}]")

    if isinstance(instance, dict):
        errors.extend(_validate_object(instance, schema, path))
    elif isinstance(instance, list):
        errors.extend(_validate_array(instance, schema, path))
    elif isinstance(instance, str):
        errors.extend(_validate_string(instance, schema, path))
    elif isinstance(instance, (int, float)) and not isinstance(instance, bool):
        errors.extend(_validate_number(instance, schema, path))

    for subschema in schema.get("allOf", []):
        errors.extend(validate_instance(instance, subschema, path))

    any_of = schema.get("anyOf")
    if any_of:
        branch_errors = [validate_instance(instance, sub, path) for sub in any_of]
        if all(branch for branch in branch_errors):
            joined = "; ".join(branch[0] for branch in branch_errors)
            errors.append(f"{path}: does not match any allowed variant ({joined})")

    return errors


def _matches_type(instance: Any, expected: Any) -> bool:
    """Return True when the instance matches a schema ``type`` declaration."""
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        python_type = _TYPE_MAP.get(name)
        if python_type is None:
            continue
        if name in {"integer", "number"} and isinstance(instance, bool):
            continue
        if isinstance(instance, python_type):
            return True
    return False


def _validate_object(instance: dict[str, Any], schema: dict[str, Any], path: str) -> list[str]:
    """Validate object-specific keywords."""
    errors: list[str] = []
    properties: dict[str, Any] = schema.get("properties", {})

    for key in schema.get("required", []):
        if key not in instance:
            errors.append(f"{path}: missing required property {key!r}")

    for key, value in instance.items():
        if key in properties:
            errors.extend(validate_instance(value, properties[key], f"{path}.{key}"))

    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(instance) - set(properties))
        for key in unexpected:
            errors.append(f"{path}: unexpected property {key!r}")

    return errors


def _validate_array(instance: list[Any], schema: dict[str, Any], path: str) -> list[str]:
    """Validate array-specific keywords."""
    errors: list[str] = []
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for position, item in enumerate(instance):
            errors.extend(validate_instance(item, item_schema, f"{path}[{position}]"))

    minimum_items = schema.get("minItems")
    if minimum_items is not None and len(instance) < minimum_items:
        errors.append(f"{path}: needs at least {minimum_items} item(s), got {len(instance)}")

    if schema.get("uniqueItems") and _has_duplicates(instance):
        errors.append(f"{path}: items must be unique")

    return errors


def _has_duplicates(items: Sequence[Any]) -> bool:
    """Return True when a sequence contains repeated (JSON-comparable) values."""
    seen: list[str] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key in seen:
            return True
        seen.append(key)
    return False


def _validate_string(instance: str, schema: dict[str, Any], path: str) -> list[str]:
    """Validate string-specific keywords."""
    errors: list[str] = []
    minimum_length = schema.get("minLength")
    if minimum_length is not None and len(instance) < minimum_length:
        errors.append(f"{path}: must be at least {minimum_length} character(s)")
    pattern = schema.get("pattern")
    if pattern is not None and not re.search(pattern, instance):
        errors.append(f"{path}: {instance!r} does not match pattern {pattern!r}")
    return errors


def _validate_number(instance: float, schema: dict[str, Any], path: str) -> list[str]:
    """Validate numeric keywords."""
    errors: list[str] = []
    minimum = schema.get("minimum")
    if minimum is not None and instance < minimum:
        errors.append(f"{path}: must be >= {minimum}")
    maximum = schema.get("maximum")
    if maximum is not None and instance > maximum:
        errors.append(f"{path}: must be <= {maximum}")
    return errors


# --------------------------------------------------------------------------
# Skill layout helpers
# --------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_WORK_DIR_NAME = Path(".agent-work") / "exam-prep"

WORK_FILES: dict[str, str] = {
    "progress": "progress.json",
    "manifest": "source-manifest.json",
    "scope_map": "scope-map.json",
    "topic_matrix": "exam-topic-matrix.json",
    "outline": "proposed-outline.md",
    "discrepancy_log": "discrepancy-log.json",
    "final_audit": "final-audit.json",
}

WORK_DIRS: dict[str, str] = {
    "canonical_content": "canonical-content",
    "solution_records": "solution-records",
    "verification": "verification",
    "rendered_pages": "rendered-pages",
    "pdf_text": "pdf-text",
    "edition_english": "editions/english",
    "edition_bilingual": "editions/bilingual",
}


def schema_path(name: str) -> Path:
    """Resolve a bundled schema file.

    Args:
        name: Schema stem, e.g. ``"progress-state"``.

    Returns:
        Absolute path to the schema JSON file.
    """
    return SKILL_ROOT / "schemas" / f"{name}.schema.json"


def load_schema(name: str) -> dict[str, Any]:
    """Load a bundled schema.

    Args:
        name: Schema stem, e.g. ``"verification-record"``.

    Returns:
        Parsed schema document.
    """
    return load_json(schema_path(name))


def work_file(work_dir: Path, key: str) -> Path:
    """Resolve a well-known file inside the working directory.

    Args:
        work_dir: Project working directory.
        key: Key from :data:`WORK_FILES`.

    Returns:
        Path to the file (which may not exist yet).
    """
    return work_dir / WORK_FILES[key]


def work_subdir(work_dir: Path, key: str) -> Path:
    """Resolve a well-known subdirectory inside the working directory.

    Args:
        work_dir: Project working directory.
        key: Key from :data:`WORK_DIRS`.

    Returns:
        Path to the subdirectory (which may not exist yet).
    """
    return work_dir / WORK_DIRS[key]


def iter_solution_records(work_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load every solution record in the working directory.

    Args:
        work_dir: Project working directory.

    Returns:
        ``(path, record)`` pairs sorted by filename.

    Raises:
        SkillError: If a record file is not valid JSON.
    """
    directory = work_subdir(work_dir, "solution_records")
    if not directory.is_dir():
        return []
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        records.append((path, load_json(path)))
    return records


def resolve_evidence_path(work_dir: Path, raw: str) -> Path:
    """Resolve an evidence path recorded in a solution record.

    Evidence paths are stored relative to the working directory so that records
    stay portable between machines.

    Args:
        work_dir: Project working directory.
        raw: Path string from the record.

    Returns:
        Absolute path.
    """
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else (work_dir / candidate)


# --------------------------------------------------------------------------
# Optional capability probing
# --------------------------------------------------------------------------


@dataclass
class Capability:
    """Availability of one optional dependency."""

    name: str
    module: str
    purpose: str
    available: bool = False
    detail: str = ""


PDF_READ_MODULES: tuple[tuple[str, str], ...] = (
    ("pymupdf", "fitz"),
    ("pypdf", "pypdf"),
    ("pdfminer.six", "pdfminer.high_level"),
)


def probe_module(module: str) -> tuple[bool, str]:
    """Check whether a module can be imported without raising.

    Args:
        module: Importable module name.

    Returns:
        ``(available, detail)`` where detail carries a version or the error.
    """
    try:
        imported = __import__(module, fromlist=["__version__"])
    except Exception as exc:  # noqa: BLE001 - any import failure means unavailable
        return False, f"{type(exc).__name__}: {exc}"
    version = getattr(imported, "__version__", "") or getattr(imported, "version", "")
    return True, str(version)


def pdf_reader_capability() -> tuple[str | None, str]:
    """Find the first available PDF text/page reader.

    Returns:
        ``(distribution_name, detail)``; name is None when no reader exists.
    """
    for distribution, module in PDF_READ_MODULES:
        available, detail = probe_module(module)
        if available:
            return distribution, detail
    return None, "no PDF reader module found (tried: pymupdf, pypdf, pdfminer.six)"


# --------------------------------------------------------------------------
# CLI plumbing
# --------------------------------------------------------------------------


class SkillError(Exception):
    """An error that should end the process with a specific exit code."""

    def __init__(self, message: str, code: int = EXIT_CHECK_FAILED) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Report:
    """Accumulated findings of one check script."""

    check: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    skipped_reason: str | None = None

    def fail(self, message: str) -> None:
        """Record a blocking problem."""
        self.failures.append(message)

    def warn(self, message: str) -> None:
        """Record a non-blocking problem."""
        self.warnings.append(message)

    def note(self, message: str) -> None:
        """Record informational context."""
        self.notes.append(message)

    @property
    def status(self) -> str:
        """Overall outcome: ``skipped``, ``fail`` or ``pass``."""
        if self.skipped_reason is not None:
            return "skipped"
        return "fail" if self.failures else "pass"

    @property
    def exit_code(self) -> int:
        """Process exit code matching :attr:`status`."""
        if self.status == "skipped":
            return EXIT_UNAVAILABLE
        return EXIT_CHECK_FAILED if self.failures else EXIT_OK

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report for ``--json`` output and audit records."""
        payload: dict[str, Any] = {
            "check": self.check,
            "status": self.status,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "notes": list(self.notes),
        }
        if self.skipped_reason is not None:
            payload["skipped_reason"] = self.skipped_reason
        if self.data:
            payload["data"] = self.data
        return payload

    def emit(self, as_json: bool = False) -> int:
        """Print the report and return the exit code.

        Args:
            as_json: Emit machine-readable JSON instead of text.

        Returns:
            Process exit code.
        """
        if as_json:
            sys.stdout.write(dump_json(self.to_dict()))
            return self.exit_code

        symbol = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIPPED"}[self.status]
        print(f"[{symbol}] {self.check}")
        if self.skipped_reason:
            print(f"  skipped: {self.skipped_reason}")
        for message in self.notes:
            print(f"  - {message}")
        for message in self.warnings:
            print(f"  ! {message}")
        for message in self.failures:
            print(f"  x {message}")
        return self.exit_code


def add_common_arguments(parser: argparse.ArgumentParser, work_dir: bool = True) -> None:
    """Attach arguments shared by every check script.

    Args:
        parser: Parser to extend.
        work_dir: Whether the script operates on a project working directory.
    """
    if work_dir:
        parser.add_argument(
            "--work-dir",
            type=Path,
            required=True,
            help="Project working directory (e.g. <project>/.agent-work/exam-prep).",
        )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )


def cli_main(build_parser: Callable[[], argparse.ArgumentParser],
             handler: Callable[[argparse.Namespace], int],
             argv: Sequence[str] | None = None) -> int:
    """Standard entry point wrapper for every script in this skill.

    Args:
        build_parser: Factory returning the script's argument parser.
        handler: Function performing the work; returns an exit code.
        argv: Argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code. :class:`SkillError` is reported on stderr with its
        own code so callers can distinguish "check failed" from "cannot run".
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return handler(args)
    except SkillError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
