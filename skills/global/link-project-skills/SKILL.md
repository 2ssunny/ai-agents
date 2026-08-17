---
name: link-project-skills
description: Connect a project to its centralized project-specific skills by creating safe Claude and/or Codex directory junctions. Use when the user asks to link skills, set up project skills, or repair project skill discovery.
---

# Link Project Skills

Project-specific skills live under `skills/projects/{project}` in the central
`ai-agents` repository. Expose that directory through host-specific junctions:

- Claude: `{project-root}/.claude/skills`
- Codex: `{project-root}/.agents/skills`

## 1. Resolve the central repository

Do not assume a fixed clone path.

1. Inspect `~/.agents/skills` and `~/.claude/skills` for an existing junction.
2. A valid target ends in `skills/global`; resolve the repository root two
   levels above that target.
3. Verify that `global-instructions/global_rule.md` exists under the resolved
   root.
4. If neither junction resolves a valid root, ask the user for the repository
   location.

## 2. Resolve project and hosts

- Use the Git root as `{project-root}` when available.
- Derive `{project}` from the project root folder name, then check whether a
  matching central project folder already exists.
- Link the host or hosts requested by the user. When the request says only
  "link project skills", link both Claude and Codex if both are installed.

## 3. Prepare the target

Create `skills/projects/{project}` when it does not exist. Do not populate it
with placeholder files.

Before creating a junction:

- If the destination is already a junction to the correct target, leave it.
- If it is a junction to a different target, report the mismatch and ask
  before replacing it.
- If it is a real directory with content, do not delete or move it without the
  user's explicit approval.

## 4. Create Windows junctions

Create parent directories first, then use native PowerShell:

```powershell
New-Item -ItemType Junction -Path '<project-root>\.agents\skills' -Target '<ai-agents-root>\skills\projects\<project>'
New-Item -ItemType Junction -Path '<project-root>\.claude\skills' -Target '<ai-agents-root>\skills\projects\<project>'
```

On macOS or Linux, create equivalent symbolic links with `ln -s` after
resolving and verifying both absolute paths.

## 5. Ignore machine-specific links

Ensure the project `.gitignore` contains the paths for the hosts linked:

```gitignore
.agents/skills
.claude/skills
```

Preserve existing `.gitignore` content and unrelated user changes.

## Verification

Inspect each created path and verify its `LinkType` and `Target`. Confirm the
target contains the expected `SKILL.md` files. Report that newly linked skills
may require a new Codex or Claude session before appearing in selectors.
