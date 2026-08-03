#!/usr/bin/env python3
"""Audit the verification *evidence* attached to worked solutions.

WHAT THIS DOES NOT DO
---------------------
This script cannot solve engineering problems. It has no solver, no symbolic
algebra, and no knowledge of thermodynamics or structures. It cannot tell you
whether an answer is right. Any tool claiming to verify arbitrary coursework
calculations automatically would be lying, which is why this one is called
`verify_evidence` and not `verify_calculations`.

WHAT THIS DOES
--------------
It audits the record of verification work that a human or agent actually did:

  * every record conforms to the verification-record schema;
  * every check the subject profile demands is present, and passed (or is marked
    not_applicable with a stated reason) before a settled status is allowed;
  * every evidence item points at a file that really exists;
  * the recorded content hash still matches the canonical text, so a record
    cannot silently survive an edit to the problem it verified (staleness);
  * official-solution disagreements are linked to the discrepancy log;
  * registered per-problem verification hooks, when `--run-hooks` is given, exit
    zero. Hooks are the only place real numerical checking happens, and they are
    written per problem by whoever solved it.

Exit codes: 0 evidence complete, 1 evidence incomplete or stale, 2 usage,
3 PyYAML missing for a YAML profile, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    EVIDENCE_REQUIRED_STATUSES,
    SETTLED_STATUSES,
    SKILL_ROOT,
    UNRESOLVED_STATUSES,
    Report,
    SkillError,
    block_index,
    cli_main,
    iter_solution_records,
    load_json,
    load_schema,
    load_yaml,
    parse_blocks,
    read_text,
    resolve_evidence_path,
    validate_instance,
    work_file,
)

#: Check results that satisfy a required check.
ACCEPTED_CHECK_RESULTS: frozenset[str] = frozenset({"pass", "not_applicable"})

#: Evidence kinds that must point at a real file.
PATH_BACKED_EVIDENCE: frozenset[str] = frozenset(
    {"recorded_derivation", "independent_recomputation", "verification_script"}
)

#: Seconds a single verification hook may run before it is killed.
HOOK_TIMEOUT_SECONDS = 120


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="verify_evidence.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Project working directory containing solution-records/.",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="Profile file. Defaults to the bundled profile named by each record's profile_id.",
    )
    parser.add_argument(
        "--run-hooks",
        action="store_true",
        help=(
            "Execute registered per-problem verification scripts. Off by default because "
            "it runs code from the working directory."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def load_profile(profile_id: str, override: Path | None) -> dict[str, Any]:
    """Load the profile that defines a record's verification contract.

    Args:
        profile_id: Profile referenced by the record.
        override: Explicit profile path from the command line, if any.

    Returns:
        Parsed profile document.

    Raises:
        SkillError: If the profile cannot be found or read.
    """
    if override is not None:
        return load_yaml(override)
    bundled = SKILL_ROOT / "profiles" / f"{profile_id}.yaml"
    if not bundled.is_file():
        raise SkillError(
            f"no bundled profile named {profile_id!r} ({bundled} not found); "
            "pass --profile to point at the project's own profile file",
            4,
        )
    return load_yaml(bundled)


def audit_record(
    record: dict[str, Any],
    label: str,
    profile: dict[str, Any],
    work_dir: Path,
    report: Report,
    run_hooks: bool,
) -> str:
    """Audit one solution record.

    Args:
        record: Parsed record.
        label: Filename used in messages.
        profile: Profile defining the required checks.
        work_dir: Working directory, used to resolve evidence paths.
        report: Report to accumulate findings into.
        run_hooks: Whether to execute registered verification scripts.

    Returns:
        The record's status, or ``"INVALID"`` when it failed schema validation.
    """
    status = str(record.get("status"))
    before = len(report.failures)

    # Semantic checks run first so their specific messages lead the report; the
    # schema's structural anyOf produces a correct but unhelpfully broad message
    # for the same defect.
    if status in EVIDENCE_REQUIRED_STATUSES:
        _audit_required_checks(record, label, profile, report)
        _audit_evidence(record, label, work_dir, report, run_hooks)
    elif status in UNRESOLVED_STATUSES:
        _note_unsettled(record, label, status, report)

    _audit_official_solution(record, label, status, work_dir, report)
    _audit_staleness(record, label, work_dir, report)

    errors = validate_instance(record, load_schema("verification-record"), label)
    explained = len(report.failures) > before
    for error in errors:
        if explained and "does not match any allowed variant" in error:
            continue
        report.fail(error)

    if errors and not explained:
        return "INVALID"
    return status


def _audit_required_checks(
    record: dict[str, Any], label: str, profile: dict[str, Any], report: Report
) -> None:
    """Ensure every profile-required check is present and satisfied."""
    performed = {
        entry.get("check_id"): entry
        for entry in record.get("checks") or []
        if isinstance(entry, dict)
    }
    required = [
        item.get("check_id")
        for item in profile.get("required_checks") or []
        if isinstance(item, dict)
    ]

    for check_id in required:
        entry = performed.get(check_id)
        if entry is None:
            report.fail(
                f"{label}: status {record.get('status')} requires check {check_id!r}, "
                "which is absent — an absent check counts as not performed"
            )
            continue
        result = entry.get("result")
        if result not in ACCEPTED_CHECK_RESULTS:
            report.fail(
                f"{label}: required check {check_id!r} has result {result!r}; "
                "a settled status needs 'pass' or a justified 'not_applicable'"
            )
        elif result == "not_applicable" and not (entry.get("note") or "").strip():
            report.fail(
                f"{label}: required check {check_id!r} is marked not_applicable "
                "without a note explaining why it does not apply"
            )


def _audit_evidence(
    record: dict[str, Any], label: str, work_dir: Path, report: Report, run_hooks: bool
) -> None:
    """Ensure evidence exists on disk and, optionally, that hooks pass."""
    evidence = record.get("evidence") or []
    if not evidence:
        report.fail(
            f"{label}: status {record.get('status')} with no evidence — "
            "a solution may not be presented as verified without evidence"
        )
        return

    for position, item in enumerate(evidence):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        raw_path = item.get("path")

        if kind in PATH_BACKED_EVIDENCE:
            if not raw_path:
                report.fail(f"{label}: evidence[{position}] of kind {kind!r} has no path")
                continue
            resolved = resolve_evidence_path(work_dir, str(raw_path))
            if not resolved.exists():
                report.fail(
                    f"{label}: evidence[{position}] points at {raw_path!r}, which does not exist"
                )

        hook = item.get("script_hook")
        if hook and run_hooks:
            _run_hook(label, position, work_dir, str(hook), report)
        elif hook:
            report.note(f"{label}: hook {hook!r} registered but not run (pass --run-hooks)")


def _run_hook(label: str, position: int, work_dir: Path, hook: str, report: Report) -> None:
    """Execute one registered per-problem verification script."""
    script = resolve_evidence_path(work_dir, hook)
    if not script.is_file():
        report.fail(f"{label}: evidence[{position}] hook {hook!r} does not exist")
        return
    try:
        completed = subprocess.run(  # noqa: S603 - path comes from the project's own records
            [sys.executable, str(script)],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=HOOK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        report.fail(f"{label}: hook {hook!r} exceeded {HOOK_TIMEOUT_SECONDS}s and was killed")
        return
    except OSError as exc:
        report.fail(f"{label}: hook {hook!r} could not be executed: {exc}")
        return

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else "no output"
        report.fail(f"{label}: hook {hook!r} failed (exit {completed.returncode}): {detail}")
    else:
        report.note(f"{label}: hook {hook!r} passed")


def _note_unsettled(record: dict[str, Any], label: str, status: str, report: Report) -> None:
    """Record what an unsettled item still needs."""
    if status not in UNRESOLVED_STATUSES:
        return
    open_questions = record.get("unresolved_questions") or []
    if status != "NOT_YET_VERIFIED" and not open_questions:
        report.warn(
            f"{label}: status {status} but no unresolved_questions recorded — "
            "state what is actually missing so it can be resolved later"
        )
    report.data.setdefault("unresolved", []).append(
        {"record": label, "status": status, "open_questions": len(open_questions)}
    )


def _audit_official_solution(
    record: dict[str, Any], label: str, status: str, work_dir: Path, report: Report
) -> None:
    """Ensure disagreements with the official solution are logged, not normalised away."""
    official = record.get("official_solution")
    if not isinstance(official, dict):
        return

    agreement = official.get("agreement")
    discrepancy_id = official.get("discrepancy_id")

    if agreement == "differs" and not discrepancy_id:
        report.fail(
            f"{label}: disagrees with the official solution but records no discrepancy_id — "
            "an official-solution error must be logged, never silently normalised"
        )
    if status == "OFFICIAL_SOLUTION_CORRECTED" and agreement != "differs":
        report.fail(
            f"{label}: status OFFICIAL_SOLUTION_CORRECTED requires "
            f"official_solution.agreement == 'differs', found {agreement!r}"
        )
    if official.get("available") and agreement == "not_compared" and status in SETTLED_STATUSES:
        report.fail(
            f"{label}: an official solution is available but was never compared, "
            "yet the status is settled"
        )

    if discrepancy_id:
        _check_discrepancy_logged(str(discrepancy_id), label, work_dir, report)


def _check_discrepancy_logged(
    discrepancy_id: str, label: str, work_dir: Path, report: Report
) -> None:
    """Verify a referenced discrepancy actually appears in the log."""
    log_path = work_file(work_dir, "discrepancy_log")
    if not log_path.is_file():
        report.fail(
            f"{label}: references discrepancy {discrepancy_id!r} "
            f"but {log_path.name} is missing"
        )
        return
    log = load_json(log_path)
    entries = log.get("discrepancies") if isinstance(log, dict) else log
    known = {
        entry.get("discrepancy_id")
        for entry in (entries or [])
        if isinstance(entry, dict)
    }
    if discrepancy_id not in known:
        report.fail(
            f"{label}: discrepancy {discrepancy_id!r} is not present in {log_path.name}"
        )


def _audit_staleness(record: dict[str, Any], label: str, work_dir: Path, report: Report) -> None:
    """Detect verification performed against text that has since been edited."""
    content_hash = record.get("content_hash")
    if not isinstance(content_hash, dict):
        return

    source_file = content_hash.get("source_file")
    block_id = content_hash.get("block_id")
    recorded = content_hash.get("value")
    if not (source_file and block_id and recorded):
        return

    path = resolve_evidence_path(work_dir, str(source_file))
    if not path.is_file():
        report.fail(f"{label}: content_hash.source_file {source_file!r} does not exist")
        return

    blocks = block_index(parse_blocks(read_text(path)))
    block = blocks.get(str(block_id))
    if block is None:
        report.fail(
            f"{label}: block {block_id!r} no longer exists in {source_file} — "
            "the verified content was removed or renamed"
        )
        return

    if block.content_hash != recorded:
        report.fail(
            f"{label}: STALE — {block_id} in {source_file} was edited after verification "
            f"(recorded {recorded[:12]}…, current {block.content_hash[:12]}…). "
            "Re-verify the problem or reset the record's status."
        )
        report.data.setdefault("stale_records", []).append(label)


def handler(args: argparse.Namespace) -> int:
    """Audit every solution record in the working directory."""
    report = Report(check="verify_evidence")
    records = iter_solution_records(args.work_dir)
    if not records:
        report.warn(
            f"no solution records found in {args.work_dir / 'solution-records'} — "
            "nothing has been verified yet"
        )
        report.data["records"] = 0
        return report.emit(args.as_json)

    profiles: dict[str, dict[str, Any]] = {}
    statuses: list[str] = []

    for path, record in records:
        profile_id = str(record.get("profile_id", ""))
        if profile_id not in profiles:
            profiles[profile_id] = load_profile(profile_id, args.profile)
        statuses.append(
            audit_record(
                record, path.name, profiles[profile_id], args.work_dir, report, args.run_hooks
            )
        )

    settled = sum(1 for status in statuses if status in SETTLED_STATUSES)
    unresolved = sum(1 for status in statuses if status in UNRESOLVED_STATUSES)
    report.data.update(
        {
            "records": len(records),
            "settled": settled,
            "unresolved": unresolved,
            "hooks_executed": bool(args.run_hooks),
        }
    )
    report.note(
        f"{len(records)} record(s): {settled} settled, {unresolved} unresolved. "
        "'Settled' means the required evidence exists and the recorded checks passed — "
        "it is not an independent guarantee that the answer is correct."
    )
    if not args.run_hooks:
        report.note("per-problem hooks were NOT executed; re-run with --run-hooks to run them")
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
