# Recovery and checkpoints

## Where state lives

In the study project, never in this skill's repository:

```
<project>/.agent-work/exam-prep/
├── progress.json            the checkpoint
├── source-manifest.json     Phase 1
├── scope-map.json           Phase 2
├── exam-topic-matrix.json   Phase 2
├── proposed-outline.md      Phase 2 — what the user approved
├── canonical-content/       Phase 3 — the master text
├── solution-records/        Phase 4 — one record per worked example
├── verification/            Phase 4 — derivations, recomputations, hooks
├── discrepancy-log.json     Phase 4
├── editions/
│   ├── english/             Phase 5 — English edition source
│   └── bilingual/           Phase 5 — Korean-English edition source
├── pdf-text/                Phase 7 — text sidecars from preflight
├── rendered-pages/          Phase 7 — page images and contact sheets
└── final-audit.json         Phase 7 — recomputed every run
```

The path is configurable (`work_dir` in the project config). Keeping it inside
the study project means a project can be archived, moved or handed over whole,
and means two projects never share state.

Everything here is plain text with sorted JSON keys, so it diffs cleanly and can
be committed alongside the study project if the user wants that.

## Progress states

| State | Meaning |
|-------|---------|
| `not_started` | Directory exists, no work done |
| `in_progress` | Work is underway |
| `waiting_for_approval` | Phase 2 finished; blocked on the user |
| `blocked` | Cannot proceed — missing material, unreadable source, unanswered question |
| `audit_failed` | Documents produced, final audit did not pass |
| `complete` | Every mandatory gate passed |

`complete` is only reachable through `final_audit.py` exiting 0. Setting it by
hand is caught: `validate_state.py` rejects `complete` with any mandatory gate
false, and `final_audit.py` fails the `progress_matches_reality` gate.

## What the checkpoint records

- `current_phase` and `completed_phases`;
- `approval` — whether the outline was approved, by whom, when;
- `counts` — expected problems, records present, settled, unresolved;
- `blocking_items` — with whether each needs the user;
- `unresolved_discrepancies`;
- `artifacts` — every produced output, its path, format, and the page count
  **read from the file**;
- `pdf_preflight` — whether it ran, when, and whether it passed;
- `visual_review` — the four independent facts (see `pdf-qa.md`);
- `completion_gates` — the gate booleans as last computed;
- `tool_results` — an append-only log of script runs, so recovery knows what was
  actually executed rather than what was intended;
- `updated_at`.

`counts` must match the records on disk. `validate_state.py` counts the files and
fails on disagreement — a checkpoint claiming 40 verified problems with 12 record
files is the exact failure this catches.

## Resuming

```
python3 scripts/doctor.py --work-dir WORK          # is there state to resume?
python3 scripts/validate_state.py --work-dir WORK  # is it internally consistent?
python3 scripts/final_audit.py --work-dir WORK     # what is actually finished?
```

Then continue from `current_phase`.

**A PDF in the output directory proves nothing.** It may be from an earlier
partial run, may predate the last content edit, may have been produced before any
verification happened. Real progress is: how many worked examples have records,
how many of those are settled with evidence, whether the editions are in parity,
and whether the audit passes. `final_audit.py --json` answers all four.

The `catchup` skill reads `progress.json` and `final-audit.json` for exactly this
reason.

## Never regress a checkpoint

Before overwriting `progress.json`, compare:

```
cp WORK/progress.json WORK/progress.prev.json
# ... write the new state ...
python3 scripts/validate_state.py --work-dir WORK --against WORK/progress.prev.json
```

This fails when the new checkpoint would drop record counts, lose a completed
phase, or discard a recorded approval. A crashed or confused run that restarts
from a blank state must not be able to erase a week of verification work.

If a regression is genuinely intended — a chapter was withdrawn, records were
deliberately reset — delete the specific records first so the counts legitimately
drop, and note it in `tool_results`.

## After editing verified content

Editing canonical text invalidates the verification records that cover it. The
recovery sequence is:

1. `verify_evidence.py --work-dir WORK` reports which records went `STALE`;
2. re-check those problems — actually re-check them, do not just re-hash;
3. update each record's `content_hash.value` and `verified_at`;
4. re-render the affected editions;
5. re-run preflight, because the page count has probably changed;
6. re-run `final_audit.py`.

Skipping step 2 turns the staleness guard into a rubber stamp, which is worse
than not having it.

## Interruption mid-phase

Each phase's output is a file, so an interrupted phase leaves partial but valid
state. On resume:

- **Phase 1** — re-run `inventory_sources.py`; it preserves existing IDs and
  human corrections.
- **Phase 2** — the four artefacts are independent; produce whichever are missing.
- **Phase 3** — chapters are independent files; find which sidecars have no
  Markdown or vice versa (`final_audit.py` lists them).
- **Phase 4** — records are per-example; `all_examples_have_records` names the
  gaps.
- **Phase 5** — regenerate everything from the canonical model. Rendering is
  cheap and idempotent; never hand-patch a half-rendered document.
- **Phase 7** — every check is independently re-runnable.
