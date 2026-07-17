---
name: catchup
description: Resume interrupted or ongoing work by reconstructing session context from git state, dev logs, and open PRs. Use this whenever the user says "이어서 진행해", "계속 진행해", "continue", "resume", "where were we", "뭐 하고 있었지", or starts a session referencing unfinished work — even if they don't explicitly ask for a status summary. Also use when a previous session was cut off mid-task.
---

# Catchup — Resume Work

The user frequently resumes work across sessions. Your job: reconstruct where things left off quickly and accurately, report a one-line status, then continue the work immediately. Do not ask "what would you like to do?" — the whole point is that you figure that out.

## Step 1: Read the repository state

Run these in parallel (all read-only, always safe):

- `git status` — uncommitted changes reveal work in progress
- `git log --oneline -10` — recent commits show the trajectory
- `git branch --show-current` — a feature branch name often names the task
- `gh pr list --state open` — open PRs may be waiting for fixes, reviews, or conflict resolution

## Step 2: Read the work logs

Check `log_summary/{project}_dev_log.md` and `log_summary/{project}_summary.md` in the project root (the dual-artifact system from global rules). The dev_log's tail section usually states exactly what was in progress and what was planned next. Also check for plan documents (`plan/`, `*.plan.md`, or plan files referenced in the log).

If no log exists, rely on git evidence and recent file modification times (`git diff HEAD`, recently modified files).

## Step 3: Identify the resume point

Synthesize: what was the last completed step, and what is the next incomplete step? Look for:

- Uncommitted changes that are mid-implementation (finish them)
- A dev_log "next steps" section (do the first item)
- An open PR with failing CI or conflicts (fix it)
- A plan document with unchecked items (continue from the first unchecked one)

## Step 4: Report and resume

Report the resume point in **one or two lines** — e.g. "마지막으로 임베딩 배치 재개 로직까지 커밋됐고, 04 스크립트 검증이 남아 있네요. 이어서 진행할게요." Then immediately continue the work. Do not wait for confirmation unless the next step is destructive or requires a decision only the user can make (e.g., push, merge, deleting data).

## Step 5: Keep the log current

After making meaningful progress, update `log_summary/{project}_dev_log.md` (and the summary when architecture-level decisions happen) so the next catchup lands precisely.
