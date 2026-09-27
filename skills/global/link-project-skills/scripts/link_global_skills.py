#!/usr/bin/env python3
"""Expose every global skill to the agents installed for this user.

Global skills are the internal skills in <ai-agents>/skills/global/ plus the
external skills registered in the machine-local agent-config.json:

    "skills": {"external": {"<name>": {"path": "<local checkout>"}}}

Each one gets its own link, named after the skill, in:

    ~/.claude/skills/<name>   Claude Code
    ~/.agents/skills/<name>   Codex

With --antigravity, Antigravity's ~/.gemini/config/skills.json is also given an
entry for <ai-agents>/skills/global and one per external checkout (Antigravity
scans each entry one level deep, so an external checkout is registered as its
parent directory restricted to the checkout folder with include_only). Entries
are only ever added, never changed or removed.

Legacy layout: earlier setups made ~/.claude/skills and ~/.agents/skills
themselves junctions to <ai-agents>/skills/global. That cannot hold an external
skill without writing into this repository, so it is reported and left alone
until --migrate is given; --migrate removes only the directory link (the skills
are untouched), creates a real directory, and links every skill into it.

Safety rules are those of link_project_skills.py: real files and directories are
never deleted (`rejected`), links are removed without touching their targets,
and --dry-run changes nothing. Entries in the skill directories that this script
does not manage are left alone.

Exit codes: 0 everything is in place, 1 something was rejected, 2 usage,
3 malformed agent-config.json, 4 the repository could not be resolved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from skill_links import (
    CONFIG_FILE,
    GLOBAL_SKILLS_DIR,
    KIND_EXTERNAL,
    REPO_ROOT,
    Action,
    Catalog,
    exit_code,
    is_link,
    link_target,
    load_catalog,
    plan_link,
    remove_link,
    report,
    resolve_repo,
    same_path,
)

#: Home-relative skill directory -> the agent that reads it.
GLOBAL_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    (".claude/skills", "claude"),
    (".agents/skills", "codex"),
)

#: Antigravity's global customization root and its skill registry file.
ANTIGRAVITY_HOME = Path(".gemini")
ANTIGRAVITY_REGISTRY = ANTIGRAVITY_HOME / "config" / "skills.json"


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="link_global_skills.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--agents",
        choices=["both", "claude", "codex"],
        default="both",
        help="Which global skill directories to populate (default: both).",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Convert a legacy whole-directory link to skills/global into per-skill links.",
    )
    parser.add_argument(
        "--antigravity",
        action="store_true",
        help="Also register the skills in ~/.gemini/config/skills.json (entries are only added).",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=None,
        help="Home directory to wire (default: the current user's home).",
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
# Skill directories
# --------------------------------------------------------------------------


def prepare_root(root: Path, repo: Path, migrate: bool, dry_run: bool) -> tuple[list[Action], str]:
    """Make sure a global skill directory can hold per-skill links.

    Args:
        root: ~/.claude/skills or ~/.agents/skills.
        repo: Repository root.
        migrate: Whether to convert the legacy whole-directory link.
        dry_run: Whether to only report what would happen.

    Returns:
        The actions taken and the resulting state: ``"ready"`` (links can be
        planned normally), ``"simulated"`` (dry run of a migration; the directory
        would be empty) or ``"blocked"``.
    """
    if is_link(root):
        target = link_target(root)
        if not same_path(target, repo / GLOBAL_SKILLS_DIR):
            return [
                Action(
                    str(root),
                    str(target),
                    "rejected",
                    "this directory is a link to somewhere other than this repository's "
                    "skills/global; it was left untouched. Replace it with a real directory "
                    "yourself if you want per-skill links here.",
                )
            ], "blocked"
        detail = f"legacy whole-directory link -> {target}"
        if not migrate:
            return [
                Action(
                    str(root),
                    str(target),
                    "rejected",
                    detail + ". It exposes only internal skills and cannot hold external ones "
                    "without writing into the repository. Re-run with --migrate to convert it "
                    "to a real directory of per-skill links; the skills are not touched.",
                )
            ], "blocked"
        if dry_run:
            return [
                Action(
                    str(root), str(target), "would-replace",
                    detail + "; would convert to a real directory of per-skill links",
                )
            ], "simulated"
        try:
            remove_link(root)
        except OSError as exc:
            return [
                Action(str(root), str(target), "rejected", f"{detail}; could not remove: {exc}")
            ], "blocked"
        root.mkdir(parents=True, exist_ok=True)
        return [
            Action(
                str(root),
                str(target),
                "replaced",
                detail + "; converted to a real directory (the link was removed, "
                "its content was not)",
            )
        ], "ready"

    if root.exists() and not root.is_dir():
        return [
            Action(str(root), "", "rejected", "a file exists where a skill directory belongs")
        ], "blocked"
    return [], "ready"


def link_root(
    root: Path, catalog: Catalog, repo: Path, migrate: bool, dry_run: bool
) -> list[Action]:
    """Populate one global skill directory with a link per skill.

    Args:
        root: ~/.claude/skills or ~/.agents/skills.
        catalog: Skills to expose.
        repo: Repository root.
        migrate: Whether to convert the legacy whole-directory link.
        dry_run: Whether to only report what would happen.

    Returns:
        The actions for this directory.
    """
    actions, state = prepare_root(root, repo, migrate, dry_run)
    if state == "blocked":
        return actions
    for name, skill in sorted(catalog.skills.items()):
        link = root / name
        if state == "simulated":
            actions.append(Action(str(link), str(skill.source), "would-link", "after migration"))
        else:
            actions.append(plan_link(link, skill.source, dry_run))
    for name, (path, problem) in sorted(catalog.unavailable.items()):
        actions.append(Action(str(root / name), str(path), "rejected", problem))
    return actions


# --------------------------------------------------------------------------
# Antigravity
# --------------------------------------------------------------------------


def antigravity_entries(catalog: Catalog, repo: Path) -> list[dict[str, object]]:
    """Return the skills.json entries that expose the catalog to Antigravity."""
    entries: list[dict[str, object]] = [{"path": (repo / GLOBAL_SKILLS_DIR).as_posix()}]
    for _, skill in sorted(catalog.skills.items()):
        if skill.kind == KIND_EXTERNAL:
            entries.append(
                {"path": skill.source.parent.as_posix(), "include_only": [skill.source.name]}
            )
    return entries


def entry_covers(existing: object, wanted: dict[str, object], home: Path) -> bool:
    """Report whether an existing skills.json entry already provides a wanted one."""
    if not isinstance(existing, dict) or not isinstance(existing.get("path"), str):
        return False
    raw = existing["path"]
    if raw == "~" or raw.startswith("~/"):
        path = home / raw[2:]
    else:
        path = Path(raw)
    if not path.is_absolute() or not same_path(path, Path(str(wanted["path"]))):
        return False
    include = existing.get("include_only")
    if include is None:
        return True
    wanted_items = wanted.get("include_only")
    return isinstance(include, list) and isinstance(wanted_items, list) and all(
        item in include for item in wanted_items
    )


def register_antigravity(home: Path, catalog: Catalog, repo: Path, dry_run: bool) -> list[Action]:
    """Add missing skill entries to Antigravity's skills.json.

    Args:
        home: Home directory.
        catalog: Skills to expose.
        repo: Repository root.
        dry_run: Whether to only report what would happen.

    Returns:
        One action per wanted entry.
    """
    registry = home / ANTIGRAVITY_REGISTRY
    if not (home / ANTIGRAVITY_HOME).is_dir():
        return [
            Action(
                str(registry), "", "skipped",
                f"Antigravity is not set up for this user ({home / ANTIGRAVITY_HOME} is missing)",
            )
        ]

    data: dict[str, object] = {}
    if registry.exists():
        try:
            loaded = json.loads(registry.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return [Action(str(registry), "", "rejected", f"not valid JSON, left untouched: {exc}")]
        if not isinstance(loaded, dict) or not isinstance(loaded.get("entries", []), list):
            return [
                Action(
                    str(registry), "", "rejected",
                    'expected an object with an "entries" list; left untouched',
                )
            ]
        data = loaded

    entries: list[object] = list(data.get("entries", []))  # type: ignore[arg-type]
    actions: list[Action] = []
    added = False
    for wanted in antigravity_entries(catalog, repo):
        label = json.dumps(wanted)
        if any(entry_covers(entry, wanted, home) for entry in entries):
            actions.append(Action(str(registry), label, "skipped", f"already registered: {label}"))
            continue
        entries.append(wanted)
        added = True
        outcome = "would-link" if dry_run else "linked"
        actions.append(Action(str(registry), label, outcome, f"entry added: {label}"))

    if added and not dry_run:
        data["entries"] = entries
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return actions


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
    home = (args.home or Path(os.path.expanduser("~"))).resolve()
    catalog = load_catalog(repo, args.config or repo / CONFIG_FILE)

    actions: list[Action] = []
    for directory, agent in GLOBAL_SKILL_DIRS:
        if args.agents in ("both", agent):
            actions.extend(link_root(home / directory, catalog, repo, args.migrate, args.dry_run))
    if args.antigravity:
        actions.extend(register_antigravity(home, catalog, repo, args.dry_run))
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
        "Agents pick up new links from their next session; "
        "later edits in the linked skills are reflected immediately.",
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
