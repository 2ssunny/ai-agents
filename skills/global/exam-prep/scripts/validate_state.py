#!/usr/bin/env python3
"""Validate the progress checkpoint.

Checks the file against the schema and then the transitions that matter for
honesty: a state of `complete` with any mandatory gate false, an approval-gated
phase reached without a recorded approval, counts that disagree with the records
actually on disk, and a checkpoint that would regress a more complete one.

Exit codes: 0 valid, 1 invalid, 2 usage, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    PHASES,
    SETTLED_STATUSES,
    Report,
    cli_main,
    iter_solution_records,
    load_json,
    load_schema,
    validate_instance,
    work_file,
)

#: Gates that must hold before `state` may be `complete`.
MANDATORY_GATES: tuple[str, ...] = (
    "sources_inventoried",
    "outline_approved",
    "canonical_content_complete",
    "all_examples_have_records",
    "no_unresolved_presented_as_verified",
    "language_editions_in_parity",
    "pdf_preflight_executed",
    "page_counts_match_actual",
    "no_stale_verification_records",
)

#: Phases that may not start before the outline has been approved.
POST_APPROVAL_PHASES: frozenset[str] = frozenset(
    {"phase3_canonical_content", "phase4_verification", "phase5_generation", "phase7_qa"}
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="validate_state.py",
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
        "--against",
        type=Path,
        help="Previous checkpoint to compare against; fails if this one regresses it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def check_state(state: dict[str, Any], work_dir: Path, report: Report) -> None:
    """Apply schema and transition checks to a progress document.

    Args:
        state: Parsed progress document.
        work_dir: Working directory the state belongs to.
        report: Report to accumulate findings into.
    """
    for error in validate_instance(state, load_schema("progress-state"), "progress"):
        report.fail(error)

    gates = state.get("completion_gates")
    gates = gates if isinstance(gates, dict) else {}
    approval = state.get("approval")
    approval = approval if isinstance(approval, dict) else {}
    current_phase = state.get("current_phase")
    completed = state.get("completed_phases") or []

    if state.get("state") == "complete":
        false_gates = sorted(name for name in MANDATORY_GATES if not gates.get(name))
        for name in false_gates:
            report.fail(
                f"state is 'complete' but mandatory gate {name!r} is false — "
                "completion may not be declared while any gate is unmet"
            )

    if current_phase in POST_APPROVAL_PHASES and not approval.get("outline_approved"):
        report.fail(
            f"current_phase is {current_phase!r} but approval.outline_approved is false — "
            "drafting may not begin before the outline is approved"
        )

    if approval.get("outline_approved") and not approval.get("approved_at"):
        report.fail("approval.outline_approved is true but approved_at is empty — record when")

    if isinstance(completed, list) and current_phase in PHASES:
        phase_order = PHASES.index(current_phase)
        for phase in completed:
            if phase in PHASES and PHASES.index(phase) > phase_order:
                report.warn(
                    f"phase {phase!r} is marked complete but current_phase is earlier "
                    f"({current_phase!r}) — confirm this is a deliberate re-run"
                )

    _check_counts(state, work_dir, report)
    _check_visual_review(state, report)


def _check_counts(state: dict[str, Any], work_dir: Path, report: Report) -> None:
    """Compare recorded counts with the records actually present on disk."""
    counts = state.get("counts")
    if not isinstance(counts, dict):
        return

    records = iter_solution_records(work_dir)
    actual_present = len(records)
    actual_settled = sum(
        1 for _, record in records if record.get("status") in SETTLED_STATUSES
    )

    if counts.get("records_present") != actual_present:
        report.fail(
            f"counts.records_present={counts.get('records_present')} but "
            f"{actual_present} record file(s) exist in solution-records/"
        )
    if counts.get("settled_records") != actual_settled:
        report.fail(
            f"counts.settled_records={counts.get('settled_records')} but "
            f"{actual_settled} record(s) on disk carry a settled status"
        )

    expected = counts.get("expected_problems")
    if isinstance(expected, int) and actual_present > expected:
        report.warn(
            f"{actual_present} records exist but only {expected} problems were expected — "
            "update expected_problems or remove the extra records"
        )

    report.data["records_on_disk"] = actual_present
    report.data["settled_on_disk"] = actual_settled


def _check_visual_review(state: dict[str, Any], report: Report) -> None:
    """Ensure the four visual-review facts are not conflated."""
    review = state.get("visual_review")
    if not isinstance(review, dict):
        return

    if review.get("human_visual_review_recorded") and not review.get("human_reviewer"):
        report.fail(
            "visual_review.human_visual_review_recorded is true but no human_reviewer is named — "
            "human review may only be claimed when a person recorded it"
        )
    if review.get("human_visual_review_recorded") and not review.get("human_reviewed_at"):
        report.fail("human_visual_review_recorded is true but human_reviewed_at is empty")
    if review.get("automated_visual_heuristics_passed") and not review.get(
        "rendered_pages_generated"
    ):
        report.fail(
            "automated_visual_heuristics_passed is true without rendered_pages_generated — "
            "heuristics cannot pass on pages that were never rendered"
        )


def check_no_regression(current: dict[str, Any], previous: dict[str, Any], report: Report) -> None:
    """Fail when a checkpoint would overwrite a strictly more complete one.

    Args:
        current: Checkpoint about to be written.
        previous: Checkpoint already stored.
        report: Report to accumulate findings into.
    """
    current_counts = current.get("counts") or {}
    previous_counts = previous.get("counts") or {}

    for field in ("records_present", "settled_records"):
        new_value = current_counts.get(field)
        old_value = previous_counts.get(field)
        if isinstance(new_value, int) and isinstance(old_value, int) and new_value < old_value:
            report.fail(
                f"counts.{field} would drop from {old_value} to {new_value} — "
                "never overwrite the latest valid checkpoint with a less complete state"
            )

    current_done = set(current.get("completed_phases") or [])
    previous_done = set(previous.get("completed_phases") or [])
    lost = sorted(previous_done - current_done)
    for phase in lost:
        report.fail(f"phase {phase!r} was complete in the previous checkpoint and is not here")

    if previous.get("approval", {}).get("outline_approved") and not current.get(
        "approval", {}
    ).get("outline_approved"):
        report.fail("previous checkpoint recorded an approval that this one drops")


def handler(args: argparse.Namespace) -> int:
    """Validate the checkpoint in the given working directory."""
    report = Report(check="validate_state")
    path = work_file(args.work_dir, "progress")
    report.note(f"progress: {path}")
    state = load_json(path)
    check_state(state, args.work_dir, report)
    if args.against:
        report.note(f"comparing against: {args.against}")
        check_no_regression(state, load_json(args.against), report)
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
