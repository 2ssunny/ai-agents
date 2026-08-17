# Workflow — the eight phases in detail

Read this once at the start of a project. Each phase names what must exist on
disk before the next may begin; the final audit checks those artefacts, so
skipping a phase surfaces later as a gate failure rather than as a silent gap.

Throughout, `WORK` means the project working directory, by default
`<project>/.agent-work/exam-prep/`.

---

## Phase 0 — Environment

```
python3 scripts/doctor.py --sources <sources> --output <output> --work-dir WORK
```

Reports the Python version, which optional packages are installed and what each
absence costs, whether the source and output directories are usable, whether any
PDF lacks a text layer (so OCR or visual reading is needed), and whether a
previous run left recoverable state.

Never install packages globally. If a capability is missing, either install it
inside the project's own environment or proceed and let the affected checks
report SKIPPED — a skipped check is an honest gap, a faked pass is not.

If `doctor.py` reports previous state, **stop and resume** rather than starting
over. See `recovery-and-checkpoints.md`.

**Produces:** nothing on disk. This phase only decides whether to proceed.

---

## Phase 1 — Source inventory

```
python3 scripts/inventory_sources.py --sources <sources> --work-dir WORK
python3 scripts/validate_manifest.py --work-dir WORK
```

Every input file gets an entry in `WORK/source-manifest.json` with a stable
`source_id` that must never change once assigned — canonical content cites these
IDs.

The classifier is a filename heuristic and is deliberately conservative. Review
its output: anything left `unclassified` needs a human decision, and a
misclassified file poisons everything built on it. Correct entries by hand; a
re-run keeps your corrections unless `--overwrite` is passed.

Fill in what the script could not determine (year, title, question/solution
content, exam relevance) by opening the files. Leave genuinely unknown fields
`null`. Record anything you expected but were not given under `missing_sources`
with an honest `impact`.

Rules for classification live in `source-policy.md`.

**Produces:** `WORK/source-manifest.json`.

---

## Phase 2 — Scope and exam analysis

No script — this is analysis. Produce, in `WORK`:

- `scope-map.json` — what is examined, what is explicitly not, and what is
  unclear, each with the `source_id` that settles it;
- `exam-topic-matrix.json` — past papers × topics, with question numbers, marks
  and command words;
- topic frequency and question-type analysis derived from that matrix;
- `proposed-outline.md` — chapter list, page-depth allocation, the derivations
  expected from memory, and every formula classified **DS** (on the official data
  sheet), **MEM** (must be memorised) or **DERIVE** (reconstructed under exam
  conditions).

DS classification must cite the data sheet's `source_id`. Without a data sheet in
the manifest, nothing may be classified DS — say so instead of assuming.

Details and worked method: `scope-and-exam-analysis.md`.

**Produces:** the four artefacts above.

---

## APPROVAL — hard stop

Present the inventory, the missing-source report, the scope map, the topic
matrix, the outline, the page-depth allocation and the formula classification.
Then stop and wait for the user's decision.

Proceed without stopping only when the config sets
`approval.continue_without_approval: true`. Either way, record the outcome:

```json
"approval": {
  "outline_approved": true,
  "approved_at": "2026-01-15T09:00:00+00:00",
  "approved_by": "user",
  "approval_note": "approved in session; asked for more depth on cycles"
}
```

An approval that was never recorded fails the audit, and drafting before approval
is rejected by `validate_state.py`.

---

## Phase 3 — Canonical content

Build one model in `WORK/canonical-content/`, one pair of files per chapter:

- `CH-01.md` — the prose, with ID-anchored blocks;
- `CH-01.json` — the structure: IDs, formula classifications, numerical results,
  marking points, common errors, source references.

Both language editions are generated from this. Never write them independently.
Structure and ID conventions: `canonical-content-model.md`.

**Produces:** `WORK/canonical-content/*.md` and `*.json`.

---

## Phase 4 — Verification

For each worked example and past-paper solution:

1. restate the problem from the source, exactly;
2. state every assumption, including ones the official solution left implicit;
3. select and justify the governing equations;
4. derive symbolically;
5. **compute the number independently, before reading any official answer**;
6. run the subject profile's checks;
7. only then compare against the official solution;
8. record the outcome, including any disagreement, in `WORK/solution-records/`.

```
python3 scripts/verify_evidence.py --work-dir WORK --run-hooks
```

Method, record shape and per-problem hooks: `problem-verification.md`.

**Produces:** `WORK/solution-records/*.json`, `WORK/verification/*`,
`WORK/discrepancy-log.json`.

---

## Phase 5 — Generation

Generate the edition sources into `WORK/editions/english/` and
`WORK/editions/bilingual/` — Markdown carrying the same ID anchors — then render
to DOCX/PDF in the project's output directory.

Seven outputs are supported: bilingual notes, English notes, bilingual
worked-solutions book, English worked-solutions book, calculation and discrepancy
audit report, past-paper topic matrix, final PDF QA report. Produce those the
config asks for.

The text sources are the master. Never edit a rendered PDF: fix the text and
render again. Style and page-target rules: `document-style.md`, bilingual
conventions: `bilingual-generation.md`.

**Produces:** `WORK/editions/**`, plus rendered documents in the output directory.

---

## Phase 6 — Checkpoint

After every meaningful step, update `WORK/progress.json` and validate it:

```
python3 scripts/validate_state.py --work-dir WORK --against <previous copy>
```

Counts in the checkpoint must match the records actually on disk — the validator
compares them. See `recovery-and-checkpoints.md`.

---

## Phase 7 — QA and final audit

```
python3 scripts/pdf_preflight.py <pdf> --expect-pages <n> --work-dir WORK
python3 scripts/check_english_only.py WORK/editions/english
python3 scripts/check_parity.py --english WORK/editions/english \
    --bilingual WORK/editions/bilingual --canonical WORK/canonical-content
python3 scripts/render_contact_sheet.py <pdf> --work-dir WORK
python3 scripts/final_audit.py --work-dir WORK --write
```

Then a person looks at the pages and records it:

```
python3 scripts/record_human_review.py --work-dir WORK \
    --reviewer "<name>" --pages "all 118 pages"
```

Only after `final_audit.py` exits 0 may the project be described as complete, and
the final report must still separate what was verified with evidence from what
was only checked automatically. See `pdf-qa.md` and `completion-gates.md`.

**Produces:** `WORK/final-audit.json`, `WORK/pdf-text/*.txt`,
`WORK/rendered-pages/**`.
