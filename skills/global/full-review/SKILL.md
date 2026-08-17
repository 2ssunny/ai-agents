---
name: full-review
description: Review an entire branch or all open pull requests with emphasis on security, correctness, and merge readiness. Use when the user asks for a full code review, security review, review before merging, or an independent second review pass.
---

# Full Review

Review everything in the requested scope. Do not silently narrow a full-review
request to the latest commit or a single file.

## 1. Establish scope

- For a branch review, compare the current branch with its actual base branch.
- For an all-PR review, enumerate every open pull request using an authenticated
  GitHub tool or `gh pr list --state open`.
- When the scope remains ambiguous after inspecting repository evidence, state
  the assumed scope before reviewing.

## 2. Review in priority order

Read the complete diff and relevant surrounding code.

1. **Security**
   - Exposed secrets, credentials, or machine-specific paths
   - Missing authentication or authorization checks
   - Unsafe CORS configuration
   - Missing rate limits on abuse-sensitive public endpoints
   - Injection paths and inadequate input validation
2. **Correctness**
   - Logic errors, unhandled failures, data loss, races, and broken invariants
3. **Regression risk**
   - Missing tests, migrations, compatibility handling, or rollback paths
4. **Conventions**
   - Apply project guidance and `global-instructions/code_style.md`; avoid
     low-value formatting comments that automated tooling already enforces

## 3. Respect the requested action

- If the user requested review only, report findings without modifying files.
- If the user requested review and fixes, apply clear in-scope fixes and test
  them. Ask before a materially broader redesign.
- Commit or push only when explicitly authorized, using the `push-pr` skill.

## 4. Perform an independent second pass

Use the best independent review mechanism exposed by the current host:

- In Claude, use the Codex review plugin when it is installed and callable.
- In Codex, use a separate review agent or isolated review context only when
  the user explicitly requested delegation or multi-agent work and the host
  permits it.
- Otherwise, clear the initial checklist, reread the raw diff from the base,
  and perform a second pass focused on issues missed by the first.

Triage second-pass findings rather than accepting them automatically. Apply or
recommend valid findings and explain rejected findings briefly.

## Report

Lead with findings ordered by severity. Include file and line references,
evidence, impact, and the smallest safe fix. Then summarize fixes made,
validation run, second-pass additions, and remaining risks.
