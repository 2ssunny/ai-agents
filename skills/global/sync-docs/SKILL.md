---
name: sync-docs
description: Synchronize project documentation with the current state of the code — repo docs (README, docs/, plan files), the log_summary dual artifacts (dev_log + summary), and the project's Notion pages via Notion MCP. Use whenever the user says "문서 최신화", "노션에 반영/업데이트", "log_summary 업데이트", "readme 업데이트", "docs sync", or after a batch of work lands and records need to catch up.
---

# Sync Docs

Documentation drifts behind the code every few sessions and the user repeatedly asks to re-sync it. This skill makes one pass that brings **all three layers** up to date. Don't update just the one file the user named and stop — the request "문서 최신화" means the whole set unless scoped otherwise.

## Step 1: Determine what changed

`git log --oneline -15` and `git diff` against the last documented state (the dev_log usually records the last synced point). Build a short list of user-visible changes: new features, changed behavior, architecture decisions, config/env changes.

## Step 2: Update repo documents

- `README.md` — only sections invalidated by the changes (setup steps, feature list, architecture diagram references). Don't rewrite unaffected prose.
- `docs/`, `plan/` documents — mark completed plan items, correct stale statements.

## Step 3: Update the dual artifacts

In `log_summary/`:

- `{project}_dev_log.md` — append what was done, decisions made, and next steps. Prune duplicated or contradicted older entries while you're there.
- `{project}_summary.md` — refresh the concise summary; never drop critical architectural decisions.

## Step 4: Update Notion

Use the Notion MCP tools. Project → Notion location mapping:

| Project | Notion location |
|---------|-----------------|
| scholar-orient | "Scholar Orient" teamspace → resources/docs pages |
| ssunny_quant | quant project pages (search "quant" if unsure) |
| (other) | `notion-search` for the project name; ask if nothing matches |

Update the existing page rather than creating duplicates — fetch it first, then edit the relevant sections. If the Notion MCP is not connected, say so and complete the repo-side sync anyway.

## Delegation

Documentation writing is mechanical: delegate the drafting to a **haiku** subagent when the update volume is more than a couple of files, per the orchestrate policy. Review its output before writing to Notion.

## Report

Finish with a compact list: files touched, Notion pages updated, anything intentionally skipped.
