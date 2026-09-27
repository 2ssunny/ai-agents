"""Link primitives and skill resolution shared by the ai-agents skill linkers.

A skill is a directory holding ``SKILL.md``. Two kinds are linked:

* internal skills, kept in this repository under ``skills/global/<name>``;
* external skills, kept in independently versioned repositories cloned on this
  machine and registered by name in the git-ignored ``agent-config.json``::

      "skills": {"external": {"<name>": {"path": "<local checkout>"}}}

  The checkout holds ``SKILL.md`` at its root and its frontmatter ``name`` must
  equal ``<name>``. An external skill is never copied into this repository.

Links are the only thing these helpers create or remove: a real file or
directory is never deleted, and removing a link never touches its target.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: This file is <repo>/skills/global/link-project-skills/scripts/<name>.py
REPO_ROOT = Path(__file__).resolve().parents[4]

#: Marker proving a directory really is the ai-agents repository.
REPO_MARKER = Path("global-instructions") / "global_rule.md"

#: Where internal global skills live, relative to the repository root.
GLOBAL_SKILLS_DIR = Path("skills") / "global"

#: Machine-local configuration file at the repository root (git-ignored).
CONFIG_FILE = "agent-config.json"

SKILL_FILE = "SKILL.md"

#: Skill names become link names, so they must never contain a path separator.
SKILL_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
NAME_FIELD = re.compile(r"^name:\s*['\"]?([^'\"\s]+)['\"]?\s*$", re.MULTILINE)

#: Windows extended-length prefixes that os.readlink may return.
WINDOWS_UNC_PREFIX = "\\\\?\\UNC\\"
WINDOWS_LONG_PREFIX = "\\\\?\\"

KIND_INTERNAL = "internal"
KIND_EXTERNAL = "external"
KIND_PROJECT = "project"

EXIT_OK = 0
EXIT_REJECTED = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
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


@dataclass(frozen=True)
class Skill:
    """A skill that can be linked, and where its canonical content lives."""

    name: str
    source: Path
    kind: str


@dataclass
class Catalog:
    """Every linkable skill, plus configured skills that cannot be linked."""

    skills: dict[str, Skill] = field(default_factory=dict)
    #: name -> (configured path, why it cannot be used)
    unavailable: dict[str, tuple[Path, str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        """Return every configured or available skill name, sorted."""
        return sorted(set(self.skills) | set(self.unavailable))


class ConfigError(Exception):
    """The machine-local configuration is malformed."""

    def __init__(self, path: Path, problems: list[str]) -> None:
        super().__init__(f"{path}: " + "; ".join(problems))
        self.path = path
        self.problems = problems


# --------------------------------------------------------------------------
# Paths and link primitives
# --------------------------------------------------------------------------


def normalize_path(path: Path | str) -> Path:
    """Strip the Windows extended-length prefix that os.readlink can return.

    ``os.readlink`` reports ``\\\\?\\D:\\x`` for a link to ``D:\\x`` on Windows;
    without normalisation an already-correct link would never compare equal.

    Args:
        path: Path as read from the filesystem.

    Returns:
        The same path without an extended-length prefix.
    """
    text = os.fspath(path)
    if os.name == "nt":
        if text.startswith(WINDOWS_UNC_PREFIX):
            text = "\\\\" + text[len(WINDOWS_UNC_PREFIX):]
        elif text.startswith(WINDOWS_LONG_PREFIX):
            text = text[len(WINDOWS_LONG_PREFIX):]
    return Path(text)


def comparable(path: Path | str) -> str:
    """Return a form of a path that compares equal for the same location."""
    try:
        resolved = normalize_path(path).resolve()
    except OSError:
        resolved = Path(os.path.abspath(normalize_path(path)))
    return os.path.normcase(str(normalize_path(resolved)))


def same_path(first: Path | str | None, second: Path | str | None) -> bool:
    """Report whether two paths name the same location."""
    if first is None or second is None:
        return False
    return comparable(first) == comparable(second)


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
    """Read where a link points, normalised for comparison.

    Args:
        path: Link to read.

    Returns:
        The resolved target, or None when it cannot be read.
    """
    try:
        raw = normalize_path(os.readlink(path))
    except OSError:
        try:
            return normalize_path(path.resolve())
        except OSError:
            return None
    if not raw.is_absolute():
        raw = path.parent / raw
    try:
        return normalize_path(raw.resolve())
    except OSError:
        return raw


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
        if same_path(current, target):
            return Action(str(link), str(target), "skipped", "already linked to the right target")
        state = "a broken link" if not link.exists() else "a link"
        if dry_run:
            return Action(
                str(link), str(target), "would-replace", f"{state} currently pointing at {current}"
            )
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
            str(link), str(target), "replaced", f"{state} was pointing at {current} ({mechanism})"
        )

    if dry_run:
        return Action(str(link), str(target), "would-link", "does not exist yet")

    try:
        mechanism = create_link(link, target)
    except OSError as exc:
        return Action(str(link), str(target), "rejected", f"could not create link: {exc}")
    return Action(str(link), str(target), "linked", mechanism)


# --------------------------------------------------------------------------
# Repository, configuration and skill resolution
# --------------------------------------------------------------------------


def resolve_repo(repo: Path = REPO_ROOT) -> Path:
    """Confirm that a directory is the ai-agents repository.

    Args:
        repo: Candidate root; defaults to the checkout holding this script.

    Returns:
        The repository root.

    Raises:
        SystemExit: If the path is not an ai-agents checkout.
    """
    if not (repo / REPO_MARKER).is_file():
        print(
            f"error: {repo} does not look like the ai-agents repository "
            f"({REPO_MARKER} is missing). Run this script from its place in the repo.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNRESOLVED)
    return repo


def read_skill_name(skill_dir: Path) -> str | None:
    """Read the frontmatter ``name`` of a skill directory.

    Args:
        skill_dir: Directory holding SKILL.md.

    Returns:
        The declared name, or None when there is no readable declaration.
    """
    try:
        text = (skill_dir / SKILL_FILE).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    block = FRONTMATTER.match(text)
    if block is None:
        return None
    name = NAME_FIELD.search(block.group(1))
    return name.group(1) if name else None


def internal_skills(repo: Path) -> dict[str, Skill]:
    """List the skills held in this repository under skills/global/.

    Args:
        repo: Repository root.

    Returns:
        Skills keyed by directory name.
    """
    root = repo / GLOBAL_SKILLS_DIR
    if not root.is_dir():
        return {}
    return {
        path.name: Skill(path.name, path, KIND_INTERNAL)
        for path in sorted(root.iterdir())
        if path.is_dir() and not is_link(path) and (path / SKILL_FILE).is_file()
    }


def load_external_skills(config_path: Path) -> dict[str, Path]:
    """Read the external-skill registrations from agent-config.json.

    A missing file or a missing ``skills`` section means no external skills. Keys
    beginning with ``_`` are comments and are ignored.

    Args:
        config_path: Path of agent-config.json.

    Returns:
        Configured checkout paths keyed by skill name, ``~`` expanded.

    Raises:
        ConfigError: If the file or its ``skills`` section is malformed.
    """
    if not config_path.is_file():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(config_path, [f"cannot be read as JSON: {exc}"]) from exc
    if not isinstance(data, dict):
        raise ConfigError(config_path, ["the top level must be a JSON object"])

    section = data.get("skills")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ConfigError(config_path, ['"skills" must be an object'])

    problems = [
        f'"skills.{key}" is not a known setting (expected "external")'
        for key in section
        if not key.startswith("_") and key != "external"
    ]
    external = section.get("external", {})
    if not isinstance(external, dict):
        raise ConfigError(config_path, [*problems, '"skills.external" must be an object'])

    resolved: dict[str, Path] = {}
    for name, entry in external.items():
        if name.startswith("_"):
            continue
        where = f'"skills.external.{name}"'
        if not SKILL_NAME_PATTERN.fullmatch(name):
            problems.append(f"{where}: a skill name uses only a-z, 0-9 and '-'")
            continue
        if not isinstance(entry, dict):
            problems.append(f'{where} must be an object like {{"path": "..."}}')
            continue
        unknown = sorted(key for key in entry if not key.startswith("_") and key != "path")
        if unknown:
            problems.append(f"{where}: unknown setting(s) {', '.join(unknown)}")
        value = entry.get("path")
        if not isinstance(value, str) or not value.strip():
            problems.append(f'{where}: "path" must be a non-empty string')
            continue
        path = Path(os.path.expanduser(value.strip()))
        if not path.is_absolute():
            problems.append(f'{where}: "path" must be absolute or start with ~/ (got {value!r})')
            continue
        resolved[name] = path

    if problems:
        raise ConfigError(config_path, problems)
    return resolved


def check_external(name: str, path: Path) -> str | None:
    """Explain why a configured external checkout cannot be linked.

    Args:
        name: Configured skill name.
        path: Configured checkout path.

    Returns:
        A description of the problem, or None when the checkout is usable.
    """
    if not path.exists():
        return f"external skill checkout not found at {path}; clone it or fix the path"
    if not path.is_dir():
        return f"{path} is not a directory"
    if not (path / SKILL_FILE).is_file():
        return f"{path} has no {SKILL_FILE} at its root"
    declared = read_skill_name(path)
    if declared != name:
        return f"{path / SKILL_FILE} declares name {declared!r}, not {name!r}"
    return None


def build_catalog(repo: Path, config_path: Path) -> Catalog:
    """Resolve every internal and configured external skill.

    An external registration is explicit machine-local intent, so it takes the
    name over an internal skill of the same name; that is reported as a note,
    because two copies of one skill should not exist.

    Args:
        repo: Repository root.
        config_path: Path of agent-config.json.

    Returns:
        The catalog.

    Raises:
        ConfigError: If the configuration is malformed.
    """
    catalog = Catalog(skills=internal_skills(repo))
    for name, path in load_external_skills(config_path).items():
        problem = check_external(name, path)
        if problem is not None:
            catalog.skills.pop(name, None)
            catalog.unavailable[name] = (path, problem)
            continue
        if name in catalog.skills:
            catalog.notes.append(
                f"external skill {name!r} ({path}) shadows the internal copy in "
                f"{GLOBAL_SKILLS_DIR.as_posix()}/{name}; keep only one source"
            )
        catalog.skills[name] = Skill(name, path, KIND_EXTERNAL)
    return catalog


def load_catalog(repo: Path, config_path: Path) -> Catalog:
    """Build the catalog, exiting with a clear message on malformed configuration."""
    try:
        catalog = build_catalog(repo, config_path)
    except ConfigError as exc:
        print(f"error: {exc.path} is malformed:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        raise SystemExit(EXIT_CONFIG) from exc
    for note in catalog.notes:
        print(f"note: {note}", file=sys.stderr)
    return catalog


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def exit_code(actions: list[Action]) -> int:
    """Return the exit code a list of actions calls for."""
    return EXIT_REJECTED if any(a.outcome in Action.BLOCKING for a in actions) else EXIT_OK


def report(actions: list[Action], code: int, dry_run: bool, as_json: bool, done: str) -> None:
    """Print the actions as text or JSON.

    Args:
        actions: Actions to print.
        code: Exit code that will be returned.
        dry_run: Whether nothing was changed.
        as_json: Whether to print machine-readable output.
        done: Closing line for a successful real run.
    """
    if as_json:
        print(json.dumps({"actions": [asdict(a) for a in actions], "exit_code": code}, indent=2))
        return

    counts: dict[str, int] = {}
    for action in actions:
        counts[action.outcome] = counts.get(action.outcome, 0) + 1
        print(f"  {action.outcome:>13}  {action.link}")
        if action.detail:
            print(f"                 {action.detail}")

    summary = ", ".join(f"{count} {name}" for name, count in sorted(counts.items()))
    print(f"\n{summary or 'nothing to do'}")
    if dry_run:
        print("dry run — nothing was changed")
    elif code == EXIT_OK:
        print(done)
