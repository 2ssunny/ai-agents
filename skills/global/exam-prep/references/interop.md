# Interop — how general skills should handle an exam-prep project

General-purpose skills (`catchup`, `full-review`, `orchestrate`) carry a
one-line pointer to this file instead of exam-prep's details, so their
instructions stay useful for every other project and this skill's specifics stay
in one place. Read the section for the skill you are running.

An exam-prep project is identifiable by a `.agent-work/exam-prep/` directory in
the project root. `<skill>` below is this skill's directory.

## catchup — resuming work

Git is not the source of truth here. The real state lives in
`.agent-work/exam-prep/`:

- `progress.json` — current phase, counts, blocking items, whether approval was
  recorded.
- `final-audit.json` — which completion gates currently pass.

Prefer recomputing over trusting the checkpoint, since the checkpoint can be
stale after manual edits:

```bash
python3 <skill>/scripts/final_audit.py --work-dir .agent-work/exam-prep
```

**A rendered PDF in the output directory is not evidence of completion.** Drafts
are routinely produced before verification starts, so a finished-looking
document says nothing about whether its contents were checked. Resume from the
phase recorded in `progress.json`.

## full-review — reviewing the work

The review surface is the skill's own checks, not reading the documents by eye.
Run them rather than forming an impression:

| Script | What it catches |
|---|---|
| `final_audit.py` | Completion gates that do not pass |
| `verify_evidence.py` | Settled records missing checks or evidence, and hashes invalidated by a later edit |
| `check_parity.py` | Canonical ID divergence between the two editions |
| `check_english_only.py` | Hangul left in the English edition |
| `pdf_preflight.py` | Page counts that disagree with what was reported |

Also check source coverage: every canonical chapter should cite at least one
inventoried `source_id`, and anything still `unclassified` in the manifest is
unresolved work rather than a finished decision.

## orchestrate — splitting the work

The work splits cleanly by phase: source analysis, problem solving,
verification, editing, rendering, auditing. Give each subagent its own chapters
or problem range so they do not collide on the same records.

**Only the final auditor decides completion.** A solving subagent reporting
"done" means its problems have records, not that the project is finished. Run
`final_audit.py` yourself before telling the user anything is complete.
