---
name: link-project-skills
description: Wire skills to agents by links, never copies — per-skill links under <project>/.agents/skills (Codex, Antigravity) and <project>/.claude/skills (Claude Code), the global ~/.claude/skills and ~/.agents/skills directories, and Antigravity's skills.json — for skills in the ai-agents repo and for external skill repositories registered in agent-config.json. Use when the user says "이 프로젝트에 스킬 연결해줘", "프로젝트 스킬 셋업", "link skills", "exam-prep 연결해줘", "전역 스킬 다시 연결해줘", asks to register an external skill repository, or when a project that should have skills available has none wired yet.
---

# Link Project Skills

Every skill has exactly one source and agents reach it through links. An edit to
the source reaches every agent immediately, and no skill content is duplicated
per platform or per project.

Two kinds of skill are linked:

- **Internal** — kept in this repository under `skills/global/<name>/`.
- **External** — kept in its own repository, cloned anywhere on the machine, with
  `SKILL.md` at the checkout root. Register it by name in the git-ignored
  `agent-config.json`; the path is machine-specific and is never committed:

  ```json
  "skills": { "external": { "<name>": { "path": "<local checkout>" } } }
  ```

  Paths are absolute or start with `~/`. The key must equal the frontmatter
  `name` in the checkout's `SKILL.md`; the link is named after it, whatever the
  checkout folder is called. When an external registration and an internal skill
  share a name the external one wins and a note says so — keep only one source.

## Global links

```bash
python3 <ai-agents>/skills/global/link-project-skills/scripts/link_global_skills.py \
    --dry-run --antigravity
```

Links every internal and external skill, one link per skill, into:

```
~/.claude/skills/<name>    → Claude Code
~/.agents/skills/<name>    → Codex
```

`--antigravity` also adds missing entries to `~/.gemini/config/skills.json`: one
for `skills/global` and, per external checkout, its parent directory restricted
to the checkout folder with `include_only` (Antigravity scans each entry one
level deep). Entries are only ever added, never edited or removed.

**Legacy layout.** Older setups junctioned `~/.claude/skills` and
`~/.agents/skills` as a whole to `skills/global`. That cannot hold an external
skill, so the script reports it as `rejected` and changes nothing until you pass
`--migrate`, which removes only the directory link (the skills are untouched),
creates a real directory, and links each skill into it. A link that points
anywhere else is never migrated.

| Option | Effect |
|--------|--------|
| `--agents both\|claude\|codex` | Which global directories to populate |
| `--migrate` | Convert the legacy whole-directory link |
| `--antigravity` | Register the skills in `~/.gemini/config/skills.json` |
| `--config PATH` | Use another configuration file (default `<ai-agents>/agent-config.json`) |
| `--home PATH` | Wire another home directory (tests) |
| `--dry-run` | Show every action without performing it |
| `--json` | Machine-readable report |

## Project links

```bash
python3 <ai-agents>/skills/global/link-project-skills/scripts/link_project_skills.py \
    --project . --skill exam-prep --gitignore
```

```
<project>/.agents/skills/<skill>    → consumed by Codex and Antigravity
<project>/.claude/skills/<skill>    → consumed by Claude Code
```

`--skill` accepts internal and registered external skill names.

| Option | Effect |
|--------|--------|
| `--project PATH` | Project root (default: current directory) |
| `--skill NAME` | Internal or external skill to link; repeatable |
| `--project-skills` | Also link everything under `skills/projects/<project name>/` |
| `--agents both\|claude\|codex` | Which agent directories to populate |
| `--gitignore` | Append the link directories to the project's `.gitignore` |
| `--migrate` | Convert the legacy whole-directory junction (see below) |
| `--config PATH` | Use another configuration file |
| `--dry-run` | Show every action without performing it |
| `--json` | Machine-readable report |

Earlier project wiring made `<project>/.claude/skills` **itself** a junction to
`skills/projects/<project>`. Per-skill links cannot live inside that — creating
one would write into this repository — so the script refuses until `--migrate`
converts it, exactly as for the global directories. Wiring `.agents/skills`
still proceeds while the legacy `.claude/skills` layout is in place.

Both scripts resolve the repository from their own location, so there is no
path to configure. Always `--dry-run` first when the target already has skill
directories.

## What the scripts guarantee

- **Idempotent** — re-running reports `skipped` for links already correct,
  including on Windows, where link targets read back with a `\\?\` prefix.
- **Non-destructive** — a real directory or file in the way is reported as
  `rejected` and left completely alone. You move it, not the script. Entries the
  scripts do not manage are never touched.
- **Link-only removal** — replacing a stale or broken link removes the link,
  never what it points at. On Windows that means `rmdir` on the junction, which
  is why deleting these by hand with `rm -rf` is dangerous and the scripts are
  not.
- **Explicit** — every path is reported as `linked`, `skipped`, `replaced` or
  `rejected`, and a non-zero exit means something needs a human: `1` rejected,
  `2` usage, `3` malformed `agent-config.json`, `4` unresolved repository,
  project or requested skill. An external checkout that is missing or declares
  another name is `4` when requested by `--skill`, and a `rejected` entry (the
  other skills are still linked) in the global run.

Windows gets a symbolic link when Developer Mode allows it and a directory
junction (`mklink /J`, no administrator rights) otherwise; POSIX gets symbolic
links. Claude Code and Codex both follow either kind.

## After linking

Agents pick up new skills **from their next session** — do not rely on link
creation being detected mid-session. After that, edits in the skill's source are
reflected immediately with no re-linking.

Verify:

```bash
ls -l ~/.claude/skills ~/.agents/skills                                    # POSIX
Get-ChildItem "$HOME\.claude\skills" | Select-Object Name, LinkType, Target  # Windows
```

## Tests

```bash
python -m unittest discover -s tests -t tests
```

Run from this skill's folder. Tests use temporary directories only — a
throwaway repository, home directory and configuration — and skip link tests
where links cannot be created.

## Adding a new skill

- Internal global: create `skills/global/<name>/SKILL.md`, add a row to the
  skill index in `global-instructions/global_rule.md`, then re-run
  `link_global_skills.py`.
- External: clone the skill repository, register it under `skills.external` in
  `agent-config.json`, add a row to the external skill index in
  `global-instructions/global_rule.md`, then re-run `link_global_skills.py`.
- Project-specific: create `skills/projects/<project>/<name>/SKILL.md` and re-run
  `link_project_skills.py` with `--project-skills`.
