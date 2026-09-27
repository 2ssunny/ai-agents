#!/usr/bin/env python3
"""Wire a project to skills held centrally in this ai-agents repository or in an
external skill checkout registered in agent-config.json.

Skills live in exactly one place and each project gets thin links to them, so an
edit reaches every agent immediately and no content is ever duplicated.

Two directories are created per project:

    <project>/.agents/skills/<skill>   consumed by Codex and Antigravity
    <project>/.claude/skills/<skill>   consumed by Claude Code

`--skill NAME` resolves NAME to an internal skill (skills/global/NAME) or to an
external skill registered in the machine-local agent-config.json:

    "skills": {"external": {"NAME": {"path": "<local checkout>"}}}

Windows gets a symbolic link when allowed and a directory junction otherwise (no
administrator rights needed); POSIX gets symbolic links. The operation is
idempotent: re-running reports `skipped` for links that are already correct.

Safety rules:
  * a real directory is never deleted, only reported as `rejected`;
  * removing a link removes the link, never the content it points at;
  * `--dry-run` shows every action without performing any.

Legacy layout: earlier wiring made `<project>/.claude/skills` itself a junction
to `skills/projects/<project>`. That cannot hold per-skill links — writing into
it would write into this repository. Such a layout is detected and reported;
`--migrate` converts it to a real directory holding per-skill links.

Exit codes: 0 all requested links are in place, 1 something was rejected,
2 usage, 3 malformed agent-config.json, 4 the repository, project or a skill
could not be resolved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_links import (
    CONFIG_FILE,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_UNRESOLVED,
    EXIT_USAGE,
    KIND_PROJECT,
    REPO_MARKER,
    REPO_ROOT,
    SKILL_FILE,
    Action,
    Catalog,
    Skill,
    create_link,
    exit_code,
    is_link,
    link_target,
    load_catalog,
    plan_link,
    remove_link,
    report,
    resolve_repo,
)

__all__ = [
    "EXIT_OK",
    "EXIT_REJECTED",
    "EXIT_UNRESOLVED",
    "REPO_MARKER",
    "REPO_ROOT",
    "Action",
    "create_link",
    "is_link",
    "remove_link",
    "build_parser",
    "run",
    "main",
]

#: Agent directory -> purpose, both populated with the same per-skill links.
AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    (".agents/skills", "Codex, Antigravity"),
    (".claude/skills", "Claude Code"),
)

#: Entries every wired project should ignore — the links are machine-specific.
GITIGNORE_ENTRIES: tuple[str, ...] = (".agents/skills", ".claude/skills")


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
        help="Internal or registered external skill to link, repeatable (e.g. --skill exam-prep).",
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
        "--config",
        type=Path,
        default=None,
        help=f"Machine-local configuration (default: <ai-agents>/{CONFIG_FILE}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without performing them."
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit a machine-readable report."
    )
    return parser


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------


def collect_skills(
    repo: Path, project: Path, names: list[str], project_skills: bool, catalog: Catalog
) -> list[Skill]:
    """Resolve requested skill names to their canonical directories.

    Args:
        repo: Repository root.
        project: Project root (its name selects the project-skills folder).
        names: Internal or external skill names requested.
        project_skills: Whether to include this project's own skills.
        catalog: Internal and external skills available on this machine.

    Returns:
        The skills to link.

    Raises:
        SystemExit: If a named skill does not exist or its checkout is unusable.
    """
    resolved: list[Skill] = []
    for name in names:
        if name in catalog.unavailable:
            _, problem = catalog.unavailable[name]
            print(f"error: skill {name!r} is registered but unusable: {problem}", file=sys.stderr)
            raise SystemExit(EXIT_UNRESOLVED)
        if name not in catalog.skills:
            print(
                f"error: no skill named {name!r}. Available: {', '.join(catalog.names())}",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_UNRESOLVED)
        resolved.append(catalog.skills[name])

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
            found = [path for path in sorted(folder.iterdir()) if (path / SKILL_FILE).is_file()]
            if not found:
                print(
                    f"note: {folder} exists but contains no skill "
                    f"(a skill is a <name>/SKILL.md folder).",
                    file=sys.stderr,
                )
            resolved.extend(Skill(path.name, path, KIND_PROJECT) for path in found)
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


def run(args: argparse.Namespace, repo: Path = REPO_ROOT) -> tuple[list[Action], int]:
    """Perform the wiring and return the actions plus an exit code.

    Args:
        args: Parsed command line.
        repo: ai-agents repository root (tests pass a throwaway one).

    Returns:
        The actions taken and the exit code.
    """
    repo = resolve_repo(repo)
    project = args.project.resolve()
    if not project.is_dir():
        print(f"error: project directory not found: {project}", file=sys.stderr)
        raise SystemExit(EXIT_UNRESOLVED)

    catalog = load_catalog(repo, args.config or repo / CONFIG_FILE)
    skills = collect_skills(repo, project, args.skill, args.project_skills, catalog)
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
        raise SystemExit(EXIT_USAGE)

    actions = check_legacy_layout(project, args.migrate, args.dry_run)
    legacy_blocked = any(action.outcome == "rejected" for action in actions)

    for directory, _ in agent_dirs(args.agents):
        if legacy_blocked and directory.startswith(".claude"):
            continue
        for skill in skills:
            actions.append(plan_link(project / directory / skill.name, skill.source, args.dry_run))

    if args.gitignore:
        entry = update_gitignore(project, args.dry_run)
        if entry is not None:
            actions.append(entry)

    return actions, exit_code(actions)


def main(argv: list[str] | None = None) -> int:
    """Run the linker from the command line."""
    args = build_parser().parse_args(argv)
    actions, code = run(args)
    report(
        actions,
        code,
        args.dry_run,
        args.as_json,
        "Claude Code picks up new links from the next session; "
        "later edits in the linked skill are reflected immediately.",
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
