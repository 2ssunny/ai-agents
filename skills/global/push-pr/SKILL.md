---
name: push-pr
description: Approved git push and pull-request workflow — commit with the agent author signature, push, open PRs against develop, resolve conflicts, and check CI. Use whenever the user says "push 진행해", "PR 열어", "push/pr 해", "conflict resolve해", "머지 준비해", or otherwise explicitly authorizes pushing or opening/updating pull requests. This skill is the ONLY sanctioned path to push; without an explicit user request, pushing stays forbidden.
---

# Push & PR Workflow

Global rules forbid autonomous push. When the user explicitly asks, this skill defines the exact approved procedure. Follow it precisely — deviations (wrong author, wrong base branch, co-author lines) have all been corrected by the user before and waste a review cycle.

## Commit rules

- Commit any uncommitted work first, in logical units (not one mega-commit).
- Message: Angular convention — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` with a clear scope and summary.
- **Always** append `--author="ssunny-agent <ai-agent@ssunny.me>"`.
- **Never** add `Co-Authored-By` lines or AI attribution footers — the user has explicitly rejected these.
- Never `--force`, never `--no-verify`.

## Branch and PR rules

- **Base branch is `develop`** (or the project's integration branch). Never open a PR against `main` and never push directly to `main` — the user merges to `main` themselves via GitHub.
- If currently on `main`/`develop` with local changes, create a `feat/<name>` or `fix/<name>` branch first.
- PR title follows the same Angular convention as commits. Body: concise summary of what/why, list of key changes.
- After creating PRs, if multiple are open, present the sensible **merge order** (dependency-first) in one short list.

## Conflict resolution

When asked to resolve PR conflicts (e.g. "#10 conflict resolve해"):

1. `gh pr view <n>` to identify head/base branches.
2. Fetch and merge base into the head branch locally (prefer merge over rebase — the branch is shared).
3. Resolve conflicts preserving both sides' intent; when intent is ambiguous, ask rather than guess.
4. Commit the merge (same author flag), push the head branch.

## After pushing

Check CI: `gh pr checks <n>` (or `gh run list --limit 3`). If checks fail, read the logs, fix, and push again — don't report "done" with red CI. Finish with a one-line status per PR: number, title, CI state, merge order position.
