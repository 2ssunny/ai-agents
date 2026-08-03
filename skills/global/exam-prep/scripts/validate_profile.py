#!/usr/bin/env python3
"""Validate an exam-prep subject profile.

A profile defines the verification contract for a subject: which checks a worked
example must satisfy before its solution record may claim a settled status. If a
profile is wrong, every VERIFIED claim built on it is wrong too, so this runs
before anything else uses it.

Exit codes: 0 valid, 1 invalid, 2 usage, 3 PyYAML missing, 4 unreadable file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib import (  # noqa: E402
    EXIT_UNAVAILABLE,
    FORMULA_CLASSES,
    Report,
    SkillError,
    cli_main,
    load_schema,
    load_yaml,
    validate_instance,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="validate_profile.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "profile",
        type=Path,
        nargs="+",
        help="Profile file(s) to validate (.yaml or .json).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report instead of text.",
    )
    return parser


def check_profile(profile: dict[str, Any], label: str, report: Report) -> None:
    """Apply schema and semantic checks to one profile.

    Args:
        profile: Parsed profile document.
        label: Filename used in messages.
        report: Report to accumulate findings into.
    """
    schema = load_schema("project-profile")
    for error in validate_instance(profile, schema, f"{label}"):
        report.fail(error)

    if not isinstance(profile, dict):
        return

    required = profile.get("required_checks") or []
    optional = profile.get("optional_checks") or []
    if not isinstance(required, list) or not isinstance(optional, list):
        return

    required_ids = [item.get("check_id") for item in required if isinstance(item, dict)]
    optional_ids = [item.get("check_id") for item in optional if isinstance(item, dict)]

    duplicates = sorted({cid for cid in required_ids if required_ids.count(cid) > 1})
    for check_id in duplicates:
        report.fail(f"{label}: required_checks contains {check_id!r} more than once")

    overlap = sorted(set(required_ids) & set(optional_ids))
    for check_id in overlap:
        report.fail(
            f"{label}: {check_id!r} is listed as both required and optional — "
            "a check is either mandatory for VERIFIED or it is not"
        )

    classes = profile.get("formula_classes")
    if classes is not None:
        unknown = sorted(set(classes) - set(FORMULA_CLASSES))
        for name in unknown:
            report.fail(f"{label}: unknown formula class {name!r}")

    targets = profile.get("page_targets")
    if isinstance(targets, dict):
        _check_page_targets(targets, label, report)

    report.data.setdefault("profiles", []).append(
        {
            "profile_id": profile.get("profile_id"),
            "required_check_count": len(required_ids),
            "optional_check_count": len(optional_ids),
        }
    )


def _check_page_targets(targets: dict[str, Any], label: str, report: Report) -> None:
    """Verify page guidance is internally consistent."""
    minimum = targets.get("minimum_pages")
    preferred_min = targets.get("preferred_min_pages")
    preferred_max = targets.get("preferred_max_pages")
    advisory = targets.get("maximum_advisory_pages")

    ordered = [
        ("minimum_pages", minimum),
        ("preferred_min_pages", preferred_min),
        ("preferred_max_pages", preferred_max),
        ("maximum_advisory_pages", advisory),
    ]
    present = [(name, value) for name, value in ordered if isinstance(value, int)]
    for (left_name, left), (right_name, right) in zip(present, present[1:]):
        if left > right:
            report.fail(
                f"{label}: page_targets.{left_name} ({left}) exceeds {right_name} ({right})"
            )


def handler(args: argparse.Namespace) -> int:
    """Validate every profile named on the command line."""
    report = Report(check="validate_profile")
    for path in args.profile:
        try:
            profile = load_yaml(path)
        except SkillError as exc:
            if exc.code == EXIT_UNAVAILABLE:
                report.skipped_reason = str(exc)
                return report.emit(args.as_json)
            report.fail(str(exc))
            continue
        check_profile(profile, path.name, report)
        report.note(f"{path.name}: parsed")
    return report.emit(args.as_json)


if __name__ == "__main__":
    raise SystemExit(cli_main(build_parser, handler))
