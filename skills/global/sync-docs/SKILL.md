---
name: sync-docs
description: Synchronize repository documentation and optional Notion pages with the current code and decisions. Use when the user asks to update docs, README, project plans, log summaries, Notion documentation, or perform a complete documentation sync.
---

# Sync Documentation

Bring the requested documentation into agreement with the current code and
recorded decisions. Do not invent implementation status from plans alone.

## 1. Determine what changed

Inspect recent commits, the working diff, existing documentation, and project
logs. Build a concise evidence list of user-visible behavior, architecture,
configuration, and completed plan items.

## 2. Respect scope

- For a complete documentation sync, check `README.md`, relevant `docs/` and
  `plan/` files, existing `log_summary/` artifacts, and linked Notion pages.
- For a specifically scoped request, update the named document plus only the
  directly dependent documents that would otherwise become contradictory.
- Do not create `log_summary/` unless the project already uses it, project
  guidance requires it, or the user requests it.

## 3. Update repository documents

- Change only sections invalidated by the code or decisions.
- Mark plan items complete only when repository evidence supports completion.
- Preserve useful historical decisions while removing duplicate or
  contradictory statements.
- Keep setup commands, environment requirements, and architecture references
  executable and current.

## 4. Update Notion when in scope

Use the current host's authorized Notion connector or MCP tools. Search for and
fetch the existing project page before editing it; do not create duplicates.

Locate the destination by searching for the project name, and ask only when
multiple plausible destinations remain. When a project's documentation lives
somewhere the name does not obviously match, record that mapping in the
project's own instruction file rather than here — this skill is shared and
public, so it should not carry anyone's workspace layout.

If Notion is unavailable or unauthenticated, complete the repository portion and
report the external portion as skipped.

## Delegation

Delegate drafting only when the user explicitly requested subagents or
parallel work. Use the host's default model unless the user specified another.
Review delegated text against repository evidence before saving it.

## Report

List documents changed, Notion pages updated, validation performed, and any
portion intentionally skipped.
