---
name: full-review
description: Full code review of a branch or all open PRs with a security focus (auth, CORS, rate-limiting, secrets), followed by cross-review via the Codex plugin. Use whenever the user says "전체 코드리뷰", "코드리뷰 해", "보안 점검", "codex 리뷰 돌려", "codex로 PR 리뷰시켜", or asks for a review pass before merging. Covers both self-review-and-fix and delegating review to Codex.
---

# Full Review

The user's review requests usually mean: review **everything in scope** (not just the latest diff), fix what you find, then get an independent second opinion from Codex. Deliver all three parts.

## Step 1: Establish scope

- "전체 코드리뷰" on a branch → the whole diff of the current branch against its base (`git diff develop...HEAD` or `main...HEAD`).
- "PR 다 리뷰해" → every open PR: `gh pr list --state open`.
- When ambiguous, default to the wider scope; narrowing later is cheap.

## Step 2: Self-review with security emphasis

Read the full diff. Priority order:

1. **Security** — the user cares most about this:
   - Secrets/keys/absolute paths hardcoded anywhere in the diff
   - Auth: endpoints missing authentication/authorization checks
   - CORS: wildcard origins, credentials with `*`
   - Rate limiting on public endpoints
   - Input validation on user-supplied data (SQL/command injection paths)
2. **Correctness** — logic errors, unhandled failure paths, race conditions.
3. **Conventions** — per `global-instructions/code_style.md` (only flag, don't bikeshed).

**exam-prep projects** have their own review surface. Run the skill's checks rather than reading the documents by eye: `final_audit.py` (completion gates), `verify_evidence.py` (settled records with missing checks, missing evidence, or hashes invalidated by a later edit), `check_parity.py` (canonical ID divergence between the two editions), `check_english_only.py` (Hangul in the English edition), `pdf_preflight.py` (page counts that don't match what was reported). Also check source coverage: every canonical chapter should cite at least one inventoried `source_id`, and anything left `unclassified` in the manifest is unresolved work, not a finished decision.

## Step 3: Fix

Apply fixes for confirmed issues directly (small/clear fixes immediately; larger reworks: list them and confirm scope first). Commit per push-pr rules only if the user has authorized committing.

## Step 4: Cross-review with Codex

Run `/codex:review` (the Codex plugin) for an independent pass:

- For open-PR scope, iterate over **all** open PRs, one review per PR.
- If Codex hits a token/rate limit, wait and retry once after the stated cooldown; if it still fails, report which PRs got reviewed and which are pending — don't silently drop them.
- Triage Codex findings: apply the valid ones, and explicitly note the ones you disagree with and why.

## Report

One section per scope unit (branch or PR): findings by severity, what was fixed, what Codex added, what remains open.
