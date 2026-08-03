#!/usr/bin/env python3
"""Compare the two language editions for canonical-content parity.

Both editions are generated from one canonical model, so their stable IDs must
match exactly: same chapter, section, equation, figure and worked-example IDs, in
the same order, with the same kind. Page counts and prose length are expected to
differ; identifiers and numerical results are not.

Inputs are the *text* sources of each edition (Markdown carrying the ID anchors),
not the rendered PDFs — a PDF cannot be diffed meaningfully and editing it would
not survive the next render.

Exit codes: 0 in parity, 1 divergent, 2 usage, 4 unreadable input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Block,
    Report,
    SkillError,
    cli_main,
    load_json,
    parse_blocks,
    read_text,
)

#: Block kinds whose IDs must be identical across editions.
PARITY_KINDS: frozenset[str] = frozenset(
    {"chapter", "section", "formula", "derivation", "figure", "worked_example"}
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="check_parity.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--english",
        type=Path,
        required=True,
        help="English edition source: a .md file or a directory of .md files.",
    )
    parser.add_argument(
        "--bilingual",
        type=Path,
        required=True,
        help="Korean-English edition source: a .md file or a directory of .md files.",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        help="Canonical content directory; enables numerical-result parity checking.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def collect_blocks(target: Path) -> list[Block]:
    """Parse every anchored block under a file or directory.

    Args:
        target: Markdown file, or directory searched recursively for ``*.md``.

    Returns:
        Blocks in stable order (files sorted by path, blocks in document order).

    Raises:
        SkillError: If the target does not exist or a file is malformed.
    """
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.rglob("*.md"))
    else:
        raise SkillError(f"no such file or directory: {target}", 4)

    if not files:
        raise SkillError(f"no .md files found under {target}", 4)

    blocks: list[Block] = []
    for path in files:
        blocks.extend(parse_blocks(read_text(path)))
    return blocks


def compare(english: list[Block], bilingual: list[Block], report: Report) -> None:
    """Compare two edition block lists.

    Args:
        english: Blocks from the English-only edition.
        bilingual: Blocks from the Korean-English edition.
        report: Report to accumulate findings into.
    """
    english_ids = [block.block_id for block in english if block.kind in PARITY_KINDS]
    bilingual_ids = [block.block_id for block in bilingual if block.kind in PARITY_KINDS]

    missing = [bid for bid in english_ids if bid not in set(bilingual_ids)]
    extra = [bid for bid in bilingual_ids if bid not in set(english_ids)]

    for block_id in missing:
        report.fail(
            f"{block_id}: present in the English edition, missing from the bilingual edition"
        )
    for block_id in extra:
        report.fail(
            f"{block_id}: present in the bilingual edition, missing from the English edition"
        )

    english_kinds = {block.block_id: block.kind for block in english}
    for block in bilingual:
        expected = english_kinds.get(block.block_id)
        if expected is not None and expected != block.kind:
            report.fail(
                f"{block.block_id}: kind differs — {expected!r} in English, "
                f"{block.kind!r} in bilingual"
            )

    if not missing and not extra and english_ids != bilingual_ids:
        first = _first_order_difference(english_ids, bilingual_ids)
        report.fail(
            f"content ordering differs: at position {first[0]} the English edition has "
            f"{first[1]!r} and the bilingual edition has {first[2]!r}"
        )

    report.data["english_block_count"] = len(english_ids)
    report.data["bilingual_block_count"] = len(bilingual_ids)


def _first_order_difference(left: list[str], right: list[str]) -> tuple[int, str, str]:
    """Return the first index where two ID sequences diverge."""
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index, a, b
    return min(len(left), len(right)), "<end>", "<end>"


def check_numerical_parity(
    canonical_dir: Path, english_text: str, bilingual_text: str, report: Report
) -> None:
    """Verify declared numerical results appear verbatim in both editions.

    Args:
        canonical_dir: Directory holding ``*.json`` chapter sidecars.
        english_text: Concatenated English edition source.
        bilingual_text: Concatenated bilingual edition source.
        report: Report to accumulate findings into.
    """
    sidecars = sorted(canonical_dir.glob("*.json"))
    if not sidecars:
        report.warn(f"no chapter sidecars in {canonical_dir}; numerical parity not checked")
        return

    checked = 0
    for sidecar in sidecars:
        chapter = load_json(sidecar)
        for example in chapter.get("worked_examples") or []:
            example_id = example.get("example_id", "<unknown>")
            for result in example.get("numerical_results") or []:
                value = str(result.get("value"))
                label = result.get("label", "?")
                checked += 1
                if value not in english_text:
                    report.fail(
                        f"{example_id}: numerical result {label}={value} is declared in "
                        f"{sidecar.name} but does not appear in the English edition"
                    )
                if value not in bilingual_text:
                    report.fail(
                        f"{example_id}: numerical result {label}={value} is declared in "
                        f"{sidecar.name} but does not appear in the bilingual edition"
                    )
    report.data["numerical_results_checked"] = checked


def _concat_text(target: Path) -> str:
    """Concatenate every Markdown file under a path."""
    if target.is_file():
        return read_text(target)
    return "\n".join(read_text(path) for path in sorted(target.rglob("*.md")))


def handler(args: argparse.Namespace) -> int:
    """Run the parity comparison."""
    report = Report(check="check_parity")
    english = collect_blocks(args.english)
    bilingual = collect_blocks(args.bilingual)
    compare(english, bilingual, report)

    if args.canonical:
        check_numerical_parity(
            args.canonical, _concat_text(args.english), _concat_text(args.bilingual), report
        )

    if not report.failures:
        report.note("canonical IDs, kinds and ordering match across both editions")
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
