---
name: link-project-skills
description: Wire a project to its project-specific skills in the central ai-agents repo by creating a Windows junction from <project>/.claude/skills to <ai-agents-root>/skills/projects/<project>. Use when the user says "이 프로젝트에 스킬 연결해줘", "프로젝트 스킬 셋업", "link skills", or when starting work in a project that should have project-scoped skills but has no .claude/skills yet.
---

# Link Project Skills

Project-specific skills live centrally in the ai-agents repository under `skills/projects/<project>/` so every agent shares one source of truth. Claude Code only exposes them per-project via `<project>\.claude\skills`, so each project needs a junction. This skill automates that wiring.

## Step 0: Locate the ai-agents repository root

The repo can be cloned anywhere (it differs per machine/teammate), so **never assume a fixed path** — resolve it dynamically:

1. Read the global-skills junction target — it points inside the repo:

   ```powershell
   (Get-Item "$HOME\.claude\skills").Target
   ```

   The target is `<ai-agents-root>\skills\global`, so the repo root is **two levels up** from it.
2. If that junction doesn't exist, ask the user where their ai-agents repo is cloned.
3. Sanity-check the resolved root: it must contain `global-instructions\global_rule.md`.

Use the resolved `<ai-agents-root>` everywhere below.

## Procedure

1. **Detect the project name** from the current working directory's folder name (e.g. `...\scholar-orient` → `scholar-orient`). Confirm with the user if the cwd looks like a subdirectory rather than a project root.

2. **Ensure the central folder exists**: create `<ai-agents-root>\skills\projects\<project>\` if missing. An empty folder is fine — it's the future home for this project's skills.

3. **Create the junction** (junctions don't need admin rights, unlike symlinks):

   ```
   cmd /c mklink /J "<project-root>\.claude\skills" "<ai-agents-root>\skills\projects\<project>"
   ```

   On macOS/Linux use a symlink instead: `ln -s "<ai-agents-root>/skills/projects/<project>" "<project-root>/.claude/skills"` (and resolve the repo root via `readlink ~/.claude/skills`).

   - Create `<project-root>\.claude\` first if it doesn't exist.
   - If `.claude\skills` already exists as a **real folder with content**: don't delete it silently. Ask whether to move its contents into the central folder (usually yes), then move, remove the folder, and create the junction.
   - If it's already a junction pointing at the right target, report "already wired" and stop.

4. **Gitignore**: ensure the project's `.gitignore` contains `.claude/skills` (the junction target is machine-specific; committing it breaks other machines). Append if missing.

5. **Tell the user**: skills under the central folder now appear in this project's skill list **starting from the next session** (junction creation isn't picked up mid-session). After that, edits in ai-agents are reflected immediately — no re-linking needed.

## Verification

```powershell
Get-Item "<project-root>\.claude\skills" | Select-Object LinkType, Target
```

LinkType should read `Junction` with the correct target.
