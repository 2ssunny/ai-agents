#!/usr/bin/env python3
"""Wire a project to skills held centrally in this ai-agents repository.

Skills live in exactly one place — this repository — and each project gets thin
links to them, so an edit here reaches every agent immediately and no content is
ever duplicated.

Two directories are created per project:

    <project>/.agents/skills/<skill>   consumed by Codex and Antigravity
    <project>/.claude/skills/<skill>   consumed by Claude Code

Windows gets directory junctions (no administrator rights needed), POSIX gets
symbolic links. The operation is idempotent: re-running reports `skipped` for
links that are already correct.

Safety rules:
  * a real directory is never deleted, only reported as `rejected`;
  * removing a link removes the link, never the content it points at;
  * `--dry-run` shows every action without performing any.

Legacy layout: earlier wiring made `<project>/.claude/skills` itself a junction
to `skills/projects/<project>`. That cannot hold per-skill links — writing into
it would write into this repository. Such a layout is detected and reported;
`--migrate` converts it to a real directory holding per-skill links.

Exit codes: 0 all requested links are in place, 1 something was rejected,
2 usage, 4 the repository or project could not be resolved.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

#: This file is <repo>/skills/global/link-project-skills/scripts/<name>.py
REPO_ROOT = Path(__file__).resolve().parents[4]

#: Marker proving a directory really is the ai-agents repository.
REPO_MARKER = Path("global-instructions") / "global_rule.md"

#: Agent directory -> purpose, both populated with the same per-skill links.
AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    (".agents/skills", "Codex, Antigravity"),
    (".claude/skills", "Claude Code"),
)

#: Entries every wired project should ignore — the links are machine-specific.
GITIGNORE_ENTRIES: tuple[str, ...] = (".agents/skills", ".claude/skills")

EXIT_OK = 0
EXIT_REJECTED = 1
EXIT_UNRESOLVED = 4


@dataclass
class Action:
    """One link operation and what happened to it."""

    link: str
    target: str
    outcome: str
    detail: str

    #: Outcomes that mean the caller must intervene.
    BLOCKING = ("rejected",)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="link_project_skills.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root to wire (default: the current directory).",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        metavar="NAME",
        help="Global skill to link, repeatable (e.g. --skill exam-prep).",
    )
    parser.add_argument(
        "--project-skills",
        action="store_true",
        help="Also link every skill under skills/projects/<project name>/.",
    )
    parser.add_argument(
        "--agents",
        choices=["both", "claude", "codex"],
        default="both",
        help="Which agent directories to populate (default: both).",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Convert a legacy whole-directory junction at .claude/skills into per-skill links.",
    )
    parser.add_argument(
        "--gitignore",
        action="store_true",
        help="Append the link directories to the project's .gitignore if absent.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without performing them."
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit a machine-readable report."
    )
    return parser


# --------------------------------------------------------------------------
# Link primitives
# --------------------------------------------------------------------------


def is_link(path: Path) -> bool:
    """Report whether a path is a symlink or a Windows directory junction.

    ``os.path.islink`` returns False for junctions, so the reparse tag is checked
    directly on Windows.

    Args:
        path: Path to test.

    Returns:
        True when the path is a link of either kind.
    """
    if path.is_symlink():
        return True
    if os.name != "nt":
        return False
    try:
        tag = os.lstat(path).st_reparse_tag  # type: ignore[attr-defined]
    except (OSError, AttributeError):
        return False
    return tag == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None)


def link_target(path: Path) -> Path | None:
    """Read where a link points.

    Args:
        path: Link to read.

    Returns:
        The resolved target, or None when it cannot be read.
    """
    try:
        return Path(os.readlink(path)).resolve()
    except OSError:
        try:
            return path.resolve()
        except OSError:
            return None


def remove_link(path: Path) -> None:
    """Remove a link without touching what it points at.

    ``unlink`` handles POSIX symlinks and Windows file symlinks; ``rmdir`` is what
    removes a Windows directory junction, and it removes only the junction.

    Args:
        path: Link to remove.

    Raises:
        OSError: If neither removal method succeeds.
    """
    try:
        path.unlink()
    except (OSError, PermissionError):
        os.rmdir(path)


def create_link(link: Path, target: Path) -> str:
    """Create a directory link, choosing the right mechanism for the platform.

    Args:
        link: Path to create.
        target: Existing directory to point at.

    Returns:
        A short description of the mechanism used.

    Raises:
        OSError: If the link could not be created.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    try:
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    except OSError:
        # Symlinks need Developer Mode or elevation on Windows; junctions do not.
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr.strip() or "mklink /J failed")
        return "junction"


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------


def resolve_repo() -> Path:
    """Locate the ai-agents repository this script belongs to.

    Returns:
        The repository root.

    Raises:
        SystemExit: If the resolved path is not an ai-agents checkout.
    """
    if not (REPO_ROOT / REPO_MARKER).is_file():
        print(
            f"error: {REPO_ROOT} does not look like the ai-agents repository "
            f"({REPO_MARKER} is missing). Run this script from its place in the repo.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNRESOLVED)
    return REPO_ROOT


def collect_skills(
    repo: Path, project: Path, names: list[str], project_skills: bool
) -> list[tuple[str, Path]]:
    """Resolve requested skill names to their canonical directories.

    Args:
        repo: Repository root.
        project: Project root (its name selects the project-skills folder).
        names: Global skill names requested.
        project_skills: Whether to include this project's own skills.

    Returns:
        ``(skill_name, source_directory)`` pairs.

    Raises:
        SystemExit: If a named global skill does not exist.
    """
    resolved: list[tuple[str, Path]] = []
    for name in names:
        source = repo / "skills" / "global" / name
        if not (source / "SKILL.md").is_file():
            available = sorted(
                path.name for path in (repo / "skills" / "global").iterdir() if path.is_dir()
            )
            print(
                f"error: no global skill named {name!r}. Available: {', '.join(available)}",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_UNRESOLVED)
        resolved.append((name, source))

    if project_skills:
        folder = repo / "skills" / "projects" / project.resolve().name
        if not folder.is_dir():
            print(
                f"note: this project has no skills folder yet. To add project-specific "
                f"skills, create:\n  {folder}\n"
                f"and put a <skill-name>/SKILL.md inside it, then re-run.",
                file=sys.stderr,
            )
        else:
            found = [path for path in sorted(folder.iterdir()) if (path / "SKILL.md").is_file()]
            if not found:
                print(
                    f"note: {folder} exists but contains no skill "
                    f"(a skill is a <name>/SKILL.md folder).",
                    file=sys.stderr,
                )
            resolved.extend((path.name, path) for path in found)
    return resolved


def agent_dirs(selection: str) -> list[tuple[str, str]]:
    """Return the agent directories matching the CLI selection."""
    if selection == "claude":
        return [entry for entry in AGENT_SKILL_DIRS if entry[0].startswith(".claude")]
    if selection == "codex":
        return [entry for entry in AGENT_SKILL_DIRS if entry[0].startswith(".agents")]
    return list(AGENT_SKILL_DIRS)


def check_legacy_layout(project: Path, migrate: bool, dry_run: bool) -> list[Action]:
    """Detect and optionally convert the legacy whole-directory junction.

    Args:
        project: Project root.
        migrate: Whether to convert the legacy layout.
        dry_run: Whether to only report what would happen.

    Returns:
        Actions describing what was found or done.
    """
    legacy = project / ".claude" / "skills"
    if not legacy.exists() or not is_link(legacy):
        return []

    target = link_target(legacy)
    detail = f"legacy whole-directory link -> {target}"

    if not migrate:
        return [
            Action(
                str(legacy),
                str(target),
                "rejected",
                detail
                + ". Per-skill links cannot be created inside it (they would be written "
                "into the ai-agents repository). Re-run with --migrate to convert it to a "
                "real directory of per-skill links; the skills themselves are not touched.",
            )
        ]

    if dry_run:
        return [
            Action(
                str(legacy), str(target), "would-replace",
                detail + "; would convert to a real directory",
            )
        ]

    try:
        remove_link(legacy)
    except OSError as exc:
        return [Action(str(legacy), str(target), "rejected", f"{detail}; could not remove: {exc}")]

    legacy.mkdir(parents=True, exist_ok=True)
    return [
        Action(
            str(legacy),
            str(target),
            "replaced",
            detail + "; converted to a real directory (the link was removed, its content was not)",
        )
    ]


def plan_link(link: Path, target: Path, dry_run: bool) -> Action:
    """Create one link, or report why it was not created.

    Args:
        link: Path that should become a link.
        target: Canonical skill directory.
        dry_run: Whether to only report the intended action.

    Returns:
        The action and its outcome.
    """
    if link.exists() or is_link(link):
        if not is_link(link):
            kind = "directory" if link.is_dir() else "file"
            return Action(
                str(link),
                str(target),
                "rejected",
                f"a real {kind} already exists here; it was left untouched. "
                "Move or remove it yourself if you want this skill linked.",
            )
        current = link_target(link)
        if current == target.resolve():
            return Action(str(link), str(target), "skipped", "already linked to the right target")
        if dry_run:
            return Action(str(link), str(target), "would-replace", f"currently points at {current}")
        try:
            remove_link(link)
        except OSError as exc:
            return Action(
                str(link), str(target), "rejected", f"stale link could not be removed: {exc}"
            )
        try:
            mechanism = create_link(link, target)
        except OSError as exc:
            return Action(str(link), str(target), "rejected", f"could not create link: {exc}")
        return Action(
            str(link), str(target), "replaced", f"was pointing at {current} ({mechanism})"
        )

    if dry_run:
        return Action(str(link), str(target), "would-link", "does not exist yet")

    try:
        mechanism = create_link(link, target)
    except OSError as exc:
        return Action(str(link), str(target), "rejected", f"could not create link: {exc}")
    return Action(str(link), str(target), "linked", mechanism)


def update_gitignore(project: Path, dry_run: bool) -> Action | None:
    """Append the link directories to the project's .gitignore if missing.

    Args:
        project: Project root.
        dry_run: Whether to only report the intended change.

    Returns:
        An action when a change was needed, otherwise None.
    """
    path = project / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = {line.strip() for line in existing.splitlines()}
    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in lines]
    if not missing:
        return None
    if dry_run:
        return Action(str(path), "", "would-link", f"would append: {', '.join(missing)}")

    prefix = "" if existing.endswith("\n") or not existing else "\n"
    addition = prefix + "\n# agent skill links (machine-specific)\n" + "\n".join(missing) + "\n"
    path.write_text(existing + addition, encoding="utf-8", newline="\n")
    return Action(str(path), "", "linked", f"appended: {', '.join(missing)}")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def run(args: argparse.Namespace) -> tuple[list[Action], int]:
    """Perform the wiring and return the actions plus an exit code."""
    repo = resolve_repo()
    project = args.project.resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        raise SystemExit(EXIT_UNRESOLVED)

    actions = check_legacy_layout(project, args.migrate, args.dry_run)
    legacy_blocked = any(action.outcome == "rejected" for action in actions)

    skills = collect_skills(repo, project, args.skill, args.project_skills)
    if not skills:
        if args.project_skills and not args.skill:
            print(
                "error: nothing to link — see the note above. Add --skill NAME to link a "
                "global skill in the meantime (e.g. --skill exam-prep).",
                file=sys.stderr,
            )
        else:
            print(
                "error: nothing to link. Pass --skill NAME (e.g. --skill exam-prep) "
                "and/or --project-skills.",
                file=sys.stderr,
            )
        raise SystemExit(2)

    for directory, _ in agent_dirs(args.agents):
        if legacy_blocked and directory.startswith(".claude"):
            continue
        for name, source in skills:
            actions.append(plan_link(project / directory / name, source, args.dry_run))

    if args.gitignore:
        entry = update_gitignore(project, args.dry_run)
        if entry is not None:
            actions.append(entry)

    rejected = any(action.outcome in Action.BLOCKING for action in actions)
    return actions, EXIT_REJECTED if rejected else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Run the linker from the command line."""
    args = build_parser().parse_args(argv)
    actions, code = run(args)

    if args.as_json:
        print(json.dumps({"actions": [asdict(a) for a in actions], "exit_code": code}, indent=2))
        return code

    counts: dict[str, int] = {}
    for action in actions:
        counts[action.outcome] = counts.get(action.outcome, 0) + 1
        print(f"  {action.outcome:>13}  {action.link}")
        if action.detail:
            print(f"                 {action.detail}")

    summary = ", ".join(f"{count} {name}" for name, count in sorted(counts.items()))
    print(f"\n{summary or 'nothing to do'}")
    if args.dry_run:
        print("dry run — nothing was changed")
    elif code == EXIT_OK:
        print(
            "Claude Code picks up new links from the next session; "
            "later edits in ai-agents are reflected immediately."
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
