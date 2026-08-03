# Completion gates

`final_audit.py` recomputes every gate from the files in the working directory.
Nothing written in `progress.json` is taken on trust — the checkpoint is a claim,
the files are the evidence, and where they disagree the files win.

```
python3 scripts/final_audit.py --work-dir WORK --write
python3 scripts/final_audit.py --work-dir WORK --require-human-review --json
```

Exit 0 means every mandatory gate passed. Exit 1 means it did not, and the
project is not complete regardless of what has been produced.

## The gates

| Gate | Passes when | Fails when |
|------|-------------|------------|
| `progress_state_present` | `progress.json` exists and validates | It is missing or schema-invalid |
| `sources_inventoried` | The manifest exists, validates, and lists at least one source | No manifest, or an empty one |
| `outline_approved` | Approval recorded with a timestamp | No approval, or one with no timestamp |
| `canonical_content_complete` | Chapters have both `.md` and `.json`, every declared ID has an anchored block, at least one worked example exists | A sidecar declares an ID with no block, a pair is incomplete, or there are no worked examples |
| `all_examples_have_records` | Every `worked_example` block has a solution record | Any example has none |
| `verification_evidence_complete` | Every settled record has all required checks passing and evidence that resolves | A required check is absent or failing, evidence is empty, or a path does not exist |
| `no_unresolved_presented_as_verified` | No included example is `UNRESOLVED`, `NOT_YET_VERIFIED`, `ASSUMPTION_SENSITIVE` or `INSUFFICIENT_INFORMATION` | Any is, in a pack claiming completion |
| `no_stale_verification_records` | Every content hash matches the current text | Text was edited after verification |
| `language_editions_in_parity` | Both edition directories exist and their IDs, kinds and order match | Either is missing, or they diverge |
| `required_artifacts_present` | Every artefact in `progress.artifacts` exists on disk | One is declared but absent |
| `pdf_preflight_executed` | `pdf_preflight.executed` and `passed` are both true | It was never run, or ran and failed |
| `page_counts_match_actual` | Every PDF artefact's `reported_page_count` equals the count read from the file | They differ, none was reported, or the count could not be read at all |
| `human_visual_review_recorded` | A person recorded a review, with their name | Nobody did — **advisory** unless `--require-human-review` |
| `progress_matches_reality` | `state` is not `complete` while a mandatory gate fails | It is |

Every gate except `human_visual_review_recorded` is mandatory.

## Why `page_counts_match_actual` fails on an unreadable PDF

If no reader can open the file, the reported count cannot be confirmed. The gate
fails rather than passing with a caveat, because the alternative is reporting a
page count as fact when nothing verified it — one of the honesty rules this skill
exists to enforce. Install a PDF reader or do not report a page count.

## What the audit cannot check

Stated plainly so the pass is not over-read:

- **Whether the mathematics is right.** The audit checks that verification was
  performed and recorded, not that its conclusions are correct. A wrong answer
  with complete, honest evidence passes every gate.
- **Whether the content is well explained**, at the right level, or useful for
  revision.
- **Whether the scope analysis was correct** — a topic wrongly marked
  non-examined is invisible to the audit.
- **Whether a figure renders legibly.** Only a human looking at it can tell.
- **Whether an official solution was correctly judged wrong.**

This is why `human_visual_review_recorded` exists, and why the final report must
separate what was verified from what was merely checked.

## The final report

After a passing audit, report four things separately. Do not merge them.

1. **Verified with evidence** — count of examples with a settled status, complete
   required checks and resolvable evidence. Say what "verified" means here: the
   verification work was done and recorded, and it has not been invalidated by a
   later edit.
2. **Checked automatically only** — preflight, parity, Hangul, blank-page
   heuristics. Name which ran and which were SKIPPED for a missing dependency.
3. **Unresolved** — every `ASSUMPTION_SENSITIVE`, `INSUFFICIENT_INFORMATION`,
   `UNRESOLVED` and `NOT_YET_VERIFIED` item, plus every open discrepancy, with
   what would settle each.
4. **Human review** — who looked at what, or plainly that nobody has.

Also report: the actual page count of each PDF and that it came from the file;
every discrepancy found against official solutions and how it was resolved; any
source that could not be read; and whether the page count fell outside the
profile's preferred range and why.

## Language for the report

Say "the verification evidence is complete for 38 of 41 worked examples; 3 remain
unresolved" — not "all calculations verified".

Say "automated preflight passed; no human has reviewed the rendered pages" — not
"the document was checked".

Say "118 pages, read from the generated PDF" — not "approximately 120 pages".

Do not describe the work as "fully verified" or "production-ready" unless the
gates and the evidence actually support it.
