---
name: link-project-skills
description: Wire a project to skills held centrally in the ai-agents repo by creating per-skill links under <project>/.agents/skills (Codex, Antigravity) and <project>/.claude/skills (Claude Code). Use when the user says "이 프로젝트에 스킬 연결해줘", "프로젝트 스킬 셋업", "link skills", "exam-prep 연결해줘", or when starting work in a project that should have project-scoped or global skills available but has none wired yet.
---

# Link Project Skills

Skills live in exactly one place — this repository — and each project gets thin
links to them. An edit here reaches every agent immediately, and no skill content
is ever duplicated per platform.

Two directories per project, both pointing at the same canonical folder:

```
<project>/.agents/skills/<skill>    → consumed by Codex and Antigravity
<project>/.claude/skills/<skill>    → consumed by Claude Code
```

## Use the script

```bash
python3 <ai-agents>/skills/global/link-project-skills/scripts/link_project_skills.py \
    --project . --skill exam-prep --gitignore
```

It resolves the repository from its own location, so there is no path to
configure and nothing machine-specific to remember. Run `--help` for the full
option list.

| Option | Effect |
|--------|--------|
| `--project PATH` | Project root (default: current directory) |
| `--skill NAME` | Global skill to link; repeatable |
| `--project-skills` | Also link everything under `skills/projects/<project name>/` |
| `--agents both\|claude\|codex` | Which agent directories to populate |
| `--gitignore` | Append the link directories to the project's `.gitignore` |
| `--dry-run` | Show every action without performing it |
| `--migrate` | Convert the legacy whole-directory junction (see below) |
| `--json` | Machine-readable report |

Always `--dry-run` first when the project already has a `.claude/` or `.agents/`
directory.

## What it guarantees

- **Idempotent** — re-running reports `skipped` for links already correct.
- **Non-destructive** — a real directory or file in the way is reported as
  `rejected` and left completely alone. You move it, not the script.
- **Link-only removal** — replacing a stale link removes the link, never what it
  points at. On Windows that means `rmdir` on the junction, which is why deleting
  these by hand with `rm -rf` is dangerous and this script is not.
- **Explicit** — every path is reported as `linked`, `skipped`, `replaced` or
  `rejected`, and a non-zero exit means something needs a human.

Windows gets directory junctions (`mklink /J`, no administrator rights needed);
POSIX gets symbolic links. The script tries a real symlink first on Windows and
falls back to a junction, so it works with or without Developer Mode.

## Legacy layout

Earlier wiring made `<project>/.claude/skills` **itself** a junction to
`skills/projects/<project>`. Per-skill links cannot live inside that — creating
one would write into this repository through the junction.

The script detects it, refuses to write into it, and says so. Nothing is changed
until you pass `--migrate`, which removes the junction (link only; the central
content is untouched), creates a real directory in its place, and links each
skill individually. Projects wired the old way keep working until you migrate
them; only per-skill linking requires the change.

Wiring the Codex side (`.agents/skills`) still proceeds normally even while the
legacy `.claude/skills` layout is in place.

## After linking

Claude Code picks up new skills **from the next session** — link creation is not
detected mid-session. After that, edits in ai-agents are reflected immediately
with no re-linking.

Verify:

```bash
ls -l <project>/.claude/skills <project>/.agents/skills                    # POSIX
Get-Item "<project>\.claude\skills\*" | Select-Object LinkType, Target     # Windows
```

## Global skills for Claude Code

Claude Code also reads `~/.claude/skills`, junctioned once to
`<ai-agents>/skills/global`, so every global skill is already available in every
project. A per-project link is therefore redundant for Claude Code and useful
mainly for making a project's skill set explicit — the directory that genuinely
needs wiring is `.agents/skills`, which Codex and Antigravity read.

## Adding a new skill

- Global: create `skills/global/<name>/SKILL.md`, add a row to the SKILLS INDEX
  in `global-instructions/global_rule.md`, then link it into projects that need
  it.
- Project-specific: create `skills/projects/<project>/<name>/SKILL.md` and re-run
  with `--project-skills`.
