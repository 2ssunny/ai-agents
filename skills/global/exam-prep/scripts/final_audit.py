#!/usr/bin/env python3
"""Decide whether an exam-prep project may be called complete.

Every gate below is recomputed from the files in the working directory. Nothing
written in progress.json is taken on trust — a checkpoint claiming `complete`
with a failing gate is itself an audit failure.

The audit fails when:
  * a required artefact is missing or was never produced;
  * an included worked example has no verification record;
  * a record claims a settled status without the required evidence;
  * unresolved content is presented as verified;
  * the two language editions diverge in canonical IDs;
  * a reported page count differs from the count read from the PDF;
  * PDF preflight was never executed;
  * the outline approval was never recorded;
  * progress says complete while any mandatory gate is false;
  * a verification record is stale because its source text was edited afterwards.

Exit codes: 0 audit passed, 1 audit failed, 2 usage, 4 unreadable working directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    SETTLED_STATUSES,
    UNRESOLVED_STATUSES,
    Report,
    SkillError,
    cli_main,
    dump_json,
    load_json,
    load_schema,
    parse_blocks,
    read_text,
    resolve_evidence_path,
    save_json,
    validate_instance,
    work_file,
    work_subdir,
)
from check_parity import collect_blocks, compare  # noqa: E402
from pdf_text import pdf_page_count  # noqa: E402
from verify_evidence import audit_record, load_profile  # noqa: E402

AUDIT_SCHEMA_VERSION = 1


@dataclass
class Gate:
    """One completion gate and the evidence behind its verdict."""

    gate_id: str
    mandatory: bool
    passed: bool
    detail: str


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="final_audit.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Project working directory to audit.",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="Profile file override; defaults to the bundled profile named by each record.",
    )
    parser.add_argument(
        "--require-human-review",
        action="store_true",
        help="Promote the human visual review gate from advisory to mandatory.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the result to final-audit.json in the working directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def audit(
    work_dir: Path, profile_override: Path | None, require_human_review: bool
) -> dict[str, Any]:
    """Run every completion gate against a working directory.

    Args:
        work_dir: Project working directory.
        profile_override: Explicit profile path, if any.
        require_human_review: Whether the human-review gate is mandatory.

    Returns:
        A final-audit document conforming to final-audit.schema.json.

    Raises:
        SkillError: If the working directory does not exist.
    """
    if not work_dir.is_dir():
        raise SkillError(f"working directory not found: {work_dir}", 4)

    gates: list[Gate] = []
    state = _load_state(work_dir, gates)

    gates.append(_gate_sources(work_dir))
    gates.append(_gate_approval(state))

    examples, chapter_issues = _collect_examples(work_dir)
    gates.append(_gate_canonical_content(work_dir, examples, chapter_issues))

    record_summary = _audit_records(work_dir, profile_override, examples, gates)

    gates.append(_gate_parity(work_dir, state))
    gates.append(_gate_artifacts(work_dir, state))
    gates.append(_gate_preflight(state))
    gates.append(_gate_page_counts(work_dir, state))
    gates.append(_gate_human_review(state, require_human_review))
    gates.append(_gate_state_consistency(state, gates))

    failures = [
        f"{gate.gate_id}: {gate.detail}" for gate in gates if gate.mandatory and not gate.passed
    ]

    review = (state or {}).get("visual_review") or {}
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audited_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "work_dir": str(work_dir),
        "verdict": "fail" if failures else "pass",
        "gates": [asdict(gate) for gate in gates],
        "failures": failures,
        "summary": {
            "examples_total": len(examples),
            "records_present": record_summary["records_present"],
            "settled_records": record_summary["settled_records"],
            "unresolved_records": record_summary["unresolved_records"],
            "stale_records": record_summary["stale_records"],
            "human_visual_review_recorded": bool(review.get("human_visual_review_recorded")),
            "automated_checks_only": _automated_only(review),
        },
    }


def _automated_only(review: dict[str, Any]) -> list[str]:
    """List what was confirmed by script alone, with no human confirmation."""
    if review.get("human_visual_review_recorded"):
        return []
    confirmed: list[str] = []
    if review.get("automated_preflight_passed"):
        confirmed.append("PDF structural preflight")
    if review.get("automated_visual_heuristics_passed"):
        confirmed.append("blank-page and glyph heuristics")
    return confirmed


def _load_state(work_dir: Path, gates: list[Gate]) -> dict[str, Any] | None:
    """Load progress.json, recording a gate failure when it is absent or invalid."""
    path = work_file(work_dir, "progress")
    if not path.is_file():
        gates.append(Gate("progress_state_present", True, False, f"{path.name} is missing"))
        return None
    state = load_json(path)
    errors = validate_instance(state, load_schema("progress-state"), "progress")
    gates.append(
        Gate(
            "progress_state_present",
            True,
            not errors,
            "valid" if not errors else f"{len(errors)} schema error(s): {errors[0]}",
        )
    )
    return state


def _gate_sources(work_dir: Path) -> Gate:
    """Sources must have been inventoried before anything was written."""
    path = work_file(work_dir, "manifest")
    if not path.is_file():
        return Gate("sources_inventoried", True, False, f"{path.name} is missing")
    manifest = load_json(path)
    errors = validate_instance(manifest, load_schema("source-manifest"), "manifest")
    if errors:
        return Gate("sources_inventoried", True, False, f"invalid manifest: {errors[0]}")
    count = len(manifest.get("sources") or [])
    if count == 0:
        return Gate("sources_inventoried", True, False, "manifest lists no sources")
    return Gate("sources_inventoried", True, True, f"{count} source(s) inventoried")


def _gate_approval(state: dict[str, Any] | None) -> Gate:
    """The proposed outline must have been approved before drafting."""
    approval = (state or {}).get("approval") or {}
    if not approval.get("outline_approved"):
        return Gate("outline_approved", True, False, "no recorded approval of the proposed outline")
    if not approval.get("approved_at"):
        return Gate("outline_approved", True, False, "approval recorded without a timestamp")
    who = approval.get("approved_by") or "unspecified"
    return Gate("outline_approved", True, True, f"approved by {who} at {approval['approved_at']}")


def _collect_examples(work_dir: Path) -> tuple[dict[str, str], list[str]]:
    """Collect worked-example IDs declared in the canonical content.

    Args:
        work_dir: Project working directory.

    Returns:
        ``(example_id -> source filename, issues)``.
    """
    directory = work_subdir(work_dir, "canonical_content")
    examples: dict[str, str] = {}
    issues: list[str] = []
    if not directory.is_dir():
        return examples, [f"{directory} does not exist"]

    markdown_files = sorted(directory.glob("*.md"))
    if not markdown_files:
        issues.append("no canonical chapter Markdown files")

    for path in markdown_files:
        try:
            blocks = parse_blocks(read_text(path))
        except SkillError as exc:
            issues.append(f"{path.name}: {exc}")
            continue
        declared = {block.block_id for block in blocks}
        for block in blocks:
            if block.kind == "worked_example":
                examples[block.block_id] = path.name

        sidecar = path.with_suffix(".json")
        if not sidecar.is_file():
            issues.append(f"{path.name}: no matching .json sidecar")
            continue
        chapter = load_json(sidecar)
        for error in validate_instance(chapter, load_schema("canonical-chapter"), sidecar.name):
            issues.append(error)
        issues.extend(_missing_anchors(chapter, declared, sidecar.name))

    return examples, issues


def _missing_anchors(chapter: dict[str, Any], declared: set[str], label: str) -> list[str]:
    """Report IDs declared in the sidecar that have no anchored block in the Markdown."""
    wanted: list[str] = []
    for section in chapter.get("sections") or []:
        wanted.append(str(section.get("section_id")))
    for formula in chapter.get("formulas") or []:
        wanted.append(str(formula.get("equation_id")))
    for example in chapter.get("worked_examples") or []:
        wanted.append(str(example.get("example_id")))
    for figure in chapter.get("figures") or []:
        wanted.append(str(figure.get("figure_id")))
    return [
        f"{label}: declares {identifier!r} but no such block exists in the Markdown"
        for identifier in wanted
        if identifier and identifier not in declared
    ]


def _gate_canonical_content(work_dir: Path, examples: dict[str, str], issues: list[str]) -> Gate:
    """Canonical content must exist and its sidecars must agree with the Markdown."""
    del work_dir
    if issues:
        return Gate(
            "canonical_content_complete", True, False, f"{len(issues)} issue(s): {issues[0]}"
        )
    if not examples:
        return Gate(
            "canonical_content_complete",
            True,
            False,
            "no worked examples found — an outline or skeleton is not a finished pack",
        )
    return Gate(
        "canonical_content_complete", True, True, f"{len(examples)} worked example(s) declared"
    )


def _audit_records(
    work_dir: Path,
    profile_override: Path | None,
    examples: dict[str, str],
    gates: list[Gate],
) -> dict[str, int]:
    """Audit solution records and append the record-related gates."""
    # Imported here rather than at module scope to avoid a circular import.
    from _lib import iter_solution_records  # noqa: PLC0415

    records = iter_solution_records(work_dir)
    evidence_report = Report(check="final_audit.records")
    statuses: dict[str, str] = {}

    profiles: dict[str, Any] = {}
    for path, record in records:
        profile_id = str(record.get("profile_id", ""))
        if profile_id not in profiles:
            try:
                profiles[profile_id] = load_profile(profile_id, profile_override)
            except SkillError as exc:
                evidence_report.fail(f"{path.name}: {exc}")
                continue
        status = audit_record(
            record, path.name, profiles[profile_id], work_dir, evidence_report, run_hooks=False
        )
        statuses[str(record.get("example_id"))] = status

    uncovered = sorted(set(examples) - set(statuses))
    gates.append(
        Gate(
            "all_examples_have_records",
            True,
            not uncovered,
            "every worked example has a record"
            if not uncovered
            else f"{len(uncovered)} example(s) without a record: {', '.join(uncovered[:5])}",
        )
    )

    misrepresented = sorted(
        example_id for example_id, status in statuses.items() if status in UNRESOLVED_STATUSES
    )
    gates.append(
        Gate(
            "no_unresolved_presented_as_verified",
            True,
            not misrepresented,
            "no unresolved item is included as settled"
            if not misrepresented
            else (
                f"{len(misrepresented)} example(s) are still unresolved and must not appear as "
                f"verified: {', '.join(misrepresented[:5])}"
            ),
        )
    )

    stale = evidence_report.data.get("stale_records") or []
    gates.append(
        Gate(
            "no_stale_verification_records",
            True,
            not stale,
            "no record was invalidated by a later edit"
            if not stale
            else f"{len(stale)} stale record(s): {', '.join(stale[:5])}",
        )
    )

    non_stale_failures = [
        message for message in evidence_report.failures if "STALE" not in message
    ]
    gates.append(
        Gate(
            "verification_evidence_complete",
            True,
            not non_stale_failures,
            "all settled records carry the required checks and evidence"
            if not non_stale_failures
            else f"{len(non_stale_failures)} evidence problem(s): {non_stale_failures[0]}",
        )
    )

    return {
        "records_present": len(records),
        "settled_records": sum(1 for status in statuses.values() if status in SETTLED_STATUSES),
        "unresolved_records": len(misrepresented),
        "stale_records": len(stale),
    }


def _gate_parity(work_dir: Path, state: dict[str, Any] | None) -> Gate:
    """The two language editions must share canonical IDs, kinds and ordering.

    A project that declares only one edition is exempt — but the exemption is
    derived from the artefacts actually recorded, not from a claim in a config.
    """
    english = work_subdir(work_dir, "edition_english")
    bilingual = work_subdir(work_dir, "edition_bilingual")

    artifacts = (state or {}).get("artifacts") or []
    wants_bilingual = any(item.get("language") == "ko-en" for item in artifacts)

    if not bilingual.is_dir() and not wants_bilingual:
        if not english.is_dir():
            return Gate(
                "language_editions_in_parity", True, False, "no edition source directory exists"
            )
        return Gate(
            "language_editions_in_parity",
            True,
            True,
            "single-edition project: no bilingual artefact is declared, "
            "so there is nothing to compare",
        )

    if not english.is_dir() or not bilingual.is_dir():
        missing = english.name if not english.is_dir() else bilingual.name
        return Gate(
            "language_editions_in_parity",
            True,
            False,
            f"a bilingual artefact is declared but the {missing}/ edition source is missing",
        )
    try:
        report = Report(check="parity")
        compare(collect_blocks(english), collect_blocks(bilingual), report)
    except SkillError as exc:
        return Gate("language_editions_in_parity", True, False, str(exc))
    if report.failures:
        return Gate(
            "language_editions_in_parity",
            True,
            False,
            f"{len(report.failures)} divergence(s): {report.failures[0]}",
        )
    return Gate("language_editions_in_parity", True, True, "canonical IDs match across editions")


def _gate_artifacts(work_dir: Path, state: dict[str, Any] | None) -> Gate:
    """Every declared artefact must actually exist on disk."""
    artifacts = (state or {}).get("artifacts") or []
    if not artifacts:
        return Gate("required_artifacts_present", True, False, "no artefacts are recorded")
    missing = [
        item.get("path")
        for item in artifacts
        if not resolve_evidence_path(work_dir, str(item.get("path", ""))).exists()
    ]
    if missing:
        return Gate(
            "required_artifacts_present",
            True,
            False,
            f"{len(missing)} declared artefact(s) do not exist: {missing[0]}",
        )
    return Gate("required_artifacts_present", True, True, f"{len(artifacts)} artefact(s) present")


def _gate_preflight(state: dict[str, Any] | None) -> Gate:
    """PDF preflight must have been run, not merely planned."""
    preflight = (state or {}).get("pdf_preflight")
    if not isinstance(preflight, dict) or not preflight.get("executed"):
        return Gate("pdf_preflight_executed", True, False, "PDF preflight was never executed")
    if preflight.get("passed") is not True:
        return Gate("pdf_preflight_executed", True, False, "PDF preflight ran but did not pass")
    return Gate(
        "pdf_preflight_executed",
        True,
        True,
        f"executed at {preflight.get('executed_at', 'unknown time')}",
    )


def _gate_page_counts(work_dir: Path, state: dict[str, Any] | None) -> Gate:
    """Reported page counts must equal the counts read from the PDFs themselves."""
    artifacts = [
        item
        for item in ((state or {}).get("artifacts") or [])
        if item.get("format") == "pdf"
    ]
    if not artifacts:
        return Gate("page_counts_match_actual", True, False, "no PDF artefact is recorded")

    problems: list[str] = []
    for item in artifacts:
        path = resolve_evidence_path(work_dir, str(item.get("path", "")))
        reported = item.get("reported_page_count")
        if reported is None:
            problems.append(f"{path.name}: no page count reported")
            continue
        actual, detail = pdf_page_count(path)
        if actual is None:
            problems.append(
                f"{path.name}: page count could not be read ({detail}) — "
                "an unverifiable page count may not be reported as fact"
            )
        elif actual != reported:
            problems.append(f"{path.name}: reported {reported} pages, file has {actual}")

    if problems:
        return Gate("page_counts_match_actual", True, False, "; ".join(problems[:3]))
    return Gate(
        "page_counts_match_actual",
        True,
        True,
        f"{len(artifacts)} PDF page count(s) verified against the files",
    )


def _gate_human_review(state: dict[str, Any] | None, mandatory: bool) -> Gate:
    """Human visual review is only ever true when a person recorded it."""
    review = (state or {}).get("visual_review") or {}
    recorded = bool(review.get("human_visual_review_recorded"))
    if recorded and not review.get("human_reviewer"):
        return Gate(
            "human_visual_review_recorded", mandatory, False, "claimed without a named reviewer"
        )
    detail = (
        f"recorded by {review.get('human_reviewer')} at {review.get('human_reviewed_at')}"
        if recorded
        else "no human has recorded a visual review; automated checks only"
    )
    return Gate("human_visual_review_recorded", mandatory, recorded, detail)


def _gate_state_consistency(state: dict[str, Any] | None, gates: list[Gate]) -> Gate:
    """A checkpoint may not claim completion while a mandatory gate is failing."""
    if state is None:
        return Gate("progress_matches_reality", True, False, "no progress state to compare")
    failing = [gate.gate_id for gate in gates if gate.mandatory and not gate.passed]
    if state.get("state") == "complete" and failing:
        return Gate(
            "progress_matches_reality",
            True,
            False,
            f"progress says 'complete' but {len(failing)} gate(s) fail: {', '.join(failing[:3])}",
        )
    return Gate("progress_matches_reality", True, True, f"progress state is {state.get('state')!r}")


def handler(args: argparse.Namespace) -> int:
    """Run the audit and print or store the result."""
    result = audit(args.work_dir, args.profile, args.require_human_review)

    if args.write:
        save_json(work_file(args.work_dir, "final_audit"), result)

    if args.as_json:
        sys.stdout.write(dump_json(result))
        return 0 if result["verdict"] == "pass" else 1

    print(f"[{result['verdict'].upper()}] final_audit — {args.work_dir}")
    for gate in result["gates"]:
        mark = "ok  " if gate["passed"] else ("FAIL" if gate["mandatory"] else "warn")
        scope = "" if gate["mandatory"] else " (advisory)"
        print(f"  {mark} {gate['gate_id']}{scope}: {gate['detail']}")

    summary = result["summary"]
    print(
        f"  -- {summary['records_present']}/{summary['examples_total']} examples have records; "
        f"{summary['settled_records']} settled, {summary['unresolved_records']} unresolved, "
        f"{summary['stale_records']} stale"
    )
    if summary["automated_checks_only"]:
        print(
            "  -- automated only (no human confirmation): "
            + ", ".join(summary["automated_checks_only"])
        )
    if not summary["human_visual_review_recorded"]:
        print("  -- no human visual review is recorded; do not describe the pages as inspected")
    if args.write:
        print(f"  -- written to {work_file(args.work_dir, 'final_audit')}")

    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
