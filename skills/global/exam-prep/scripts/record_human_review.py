#!/usr/bin/env python3
"""Record that a human visually reviewed the rendered output.

This is the only way `human_visual_review_recorded` ever becomes true. No other
script sets it, and no agent may set it on a person's behalf: rendering pages,
generating a contact sheet and passing automated heuristics are three separate
facts, none of which means anyone looked at anything.

Run this only after a person has actually looked at the pages, and pass their
name and what they reviewed.

Exit codes: 0 recorded, 1 refused, 2 usage, 4 unreadable working directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    Report,
    SkillError,
    cli_main,
    load_json,
    save_json,
    work_file,
    work_subdir,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="record_human_review.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Project working directory containing progress.json.",
    )
    parser.add_argument(
        "--reviewer",
        required=True,
        help="Name of the person who looked at the pages. Required — this is their attestation.",
    )
    parser.add_argument(
        "--pages",
        required=True,
        help='What was reviewed, e.g. "all 118 pages" or "pp. 1-40, 95-118 (spot check)".',
    )
    parser.add_argument(
        "--note",
        help="Optional remark, e.g. what looked wrong and was fixed.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def handler(args: argparse.Namespace) -> int:
    """Record the review in progress.json."""
    report = Report(check="record_human_review")
    path = work_file(args.work_dir, "progress")
    if not path.is_file():
        raise SkillError(f"{path} not found — there is no project to record a review against", 4)

    state = load_json(path)
    rendered = work_subdir(args.work_dir, "rendered_pages")
    review = state.get("visual_review") or {
        "automated_preflight_passed": False,
        "rendered_pages_generated": False,
        "automated_visual_heuristics_passed": False,
        "human_visual_review_recorded": False,
    }

    if not rendered.is_dir() or not any(rendered.rglob("*.png")):
        report.fail(
            f"no rendered pages found under {rendered} — render the pages first so there is "
            "something a human could actually have looked at"
        )
        return report.emit(args.as_json)

    review.update(
        {
            "human_visual_review_recorded": True,
            "human_reviewer": args.reviewer,
            "human_reviewed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "pages_reviewed": args.pages,
        }
    )
    if args.note:
        review["human_review_note"] = args.note

    state["visual_review"] = review
    gates = state.setdefault("completion_gates", {})
    gates["human_visual_review_recorded"] = True
    state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    save_json(path, state)

    report.note(f"recorded: {args.reviewer} reviewed {args.pages}")
    report.note(
        "this attests only to what the reviewer looked at; it is not a statement about "
        "whether the calculations are correct"
    )
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
