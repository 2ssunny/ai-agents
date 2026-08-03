---
name: exam-prep
description: >
  Builds source-grounded exam revision notes and worked-solution books
  from lecture materials, tutorials, textbooks, data sheets, past papers,
  and official solutions. Use for consolidated STEM study packs,
  Korean-English bilingual notes, English-only notes, past-paper analysis,
  independently audited worked solutions, progress recovery, and final
  PDF quality assurance.
---

# exam-prep — verified exam notes and worked solutions

Turns a pile of course material into a consolidated revision pack whose every
worked solution carries an audit trail. The point of this skill is the gap it
refuses to close by hand-waving: **a document that renders is not a document that
was checked.** Generation and verification are separate, and the final audit only
passes when the evidence for both exists on disk.

Works for thermodynamics, structures, fluids, materials, mathematics and other
quantitative subjects via subject profiles.

## Activation

Use this skill when the request combines study material with a study deliverable:

- lecture notes, tutorials, tutorial solutions, textbooks, data sheets, formula
  booklets, past papers, official solutions, mark schemes, scope guidance;
- consolidated revision notes, exam-focused study packs, past-paper analysis;
- Korean-English bilingual academic notes, or an English-only edition;
- independently verified worked solutions;
- DOCX/PDF study-document generation, or QA of one already produced;
- resuming an interrupted study-pack project.

Do **not** use it for one-off homework help, for summarising a single document,
or for anything with no verification obligation.

## Workflow

Eight phases. Do not skip forward; each depends on the last. Full detail:
[references/workflow.md](references/workflow.md).

| Phase | What happens | Tool |
|-------|--------------|------|
| 0 Environment | check Python, optional deps, source/output dirs, prior state | `scripts/doctor.py` |
| 1 Source inventory | classify every input file; ambiguous stays `unclassified` | `scripts/inventory_sources.py`, `scripts/validate_manifest.py` |
| 2 Scope and exam analysis | scope map, topic matrix, DS/MEM/DERIVE, proposed outline | — |
| **APPROVAL** | **stop and get the user's decision on the outline** | — |
| 3 Canonical content | one text model both editions are generated from | — |
| 4 Verification | solve independently, compare, record evidence | `scripts/verify_evidence.py` |
| 5 Generation | render both editions and the audit reports | — |
| 6 Checkpoint | persist progress after every meaningful step | `scripts/validate_state.py` |
| 7 QA | preflight, parity, Hangul, rendering, final audit | `scripts/pdf_preflight.py`, `scripts/check_parity.py`, `scripts/check_english_only.py`, `scripts/render_contact_sheet.py`, `scripts/final_audit.py` |

Read [references/source-policy.md](references/source-policy.md) before Phase 1 and
[references/scope-and-exam-analysis.md](references/scope-and-exam-analysis.md)
before Phase 2.

## Approval

Phase 2 ends at a hard stop. Present the source inventory, missing-source report,
scope map, topic matrix, proposed outline, page-depth allocation and formula
classification — then **wait**.

Continue without stopping only when the project config sets
`approval.continue_without_approval: true`, and even then record the approval
fact and its origin in `progress.json`. An unrecorded approval fails the audit.

## Verification

Official solutions are a comparison source, not ground truth. Solve each problem
independently first, then compare, and when you disagree, say so and log it.

Every included worked example needs a record in `solution-records/` with one of:
`VERIFIED`, `VERIFIED_WITH_ROUNDING_DIFFERENCE`, `ASSUMPTION_SENSITIVE`,
`OFFICIAL_SOLUTION_CORRECTED`, `INSUFFICIENT_INFORMATION`, `UNRESOLVED`,
`NOT_YET_VERIFIED`.

A settled status requires **all** checks the subject profile demands, each
`pass` or a `not_applicable` with a stated reason, plus at least one evidence
item that resolves to a real file, plus the content hash of the block it verified.

`scripts/verify_evidence.py` audits those records. **It cannot solve engineering
problems** — no solver, no symbolic algebra, no subject knowledge. It checks that
the verification work was recorded, is complete, points at real artefacts, and has
not been invalidated by a later edit. Real numerical checking happens in
per-problem hooks you write, run with `--run-hooks`. See
[references/problem-verification.md](references/problem-verification.md).

## Canonical content and bilingual generation

Never write the two editions independently. Build one canonical model in
`canonical-content/` — Markdown with ID-anchored blocks plus a JSON sidecar — and
generate both editions from it, so chapter, section, equation, figure and
worked-example IDs, numerical results, assumptions, verification status, source
references and ordering all stay aligned. Page counts need not match.

Bilingual style: Korean conceptual explanation, English technical terms kept,
English model-answer phrasing where it helps the exam. Not sentence-by-sentence
duplication. Details in
[references/canonical-content-model.md](references/canonical-content-model.md) and
[references/bilingual-generation.md](references/bilingual-generation.md);
formatting in [references/document-style.md](references/document-style.md).

All work products stay editable text. DOCX and PDF are derived artefacts — edit
the text and regenerate, never patch the PDF. Editing verified text invalidates
its record, and the audit says so.

## Recovery

State lives in the study project, not here:
`<project>/.agent-work/exam-prep/` (configurable). Progress states are
`not_started`, `in_progress`, `waiting_for_approval`, `blocked`, `audit_failed`,
`complete`.

On resume, read `progress.json` and `final-audit.json` and continue from the
recorded phase. **The presence of a PDF is not evidence of completion.** Never
overwrite a checkpoint with a less complete one —
`scripts/validate_state.py --against <previous>` enforces this. See
[references/recovery-and-checkpoints.md](references/recovery-and-checkpoints.md).

## Completion gates

`scripts/final_audit.py` recomputes every gate from the files; nothing written in
`progress.json` is taken on trust. The audit **fails** when a required artefact is
missing, an included example has no record, a settled record lacks evidence,
unresolved content is presented as verified, the editions diverge in canonical
IDs, a reported page count differs from the PDF, preflight was never run, the
approval was never recorded, a record is stale, or progress claims `complete`
while any gate is false. Full list:
[references/completion-gates.md](references/completion-gates.md) and
[references/pdf-qa.md](references/pdf-qa.md).

Four separate facts, none implying another:

1. automated preflight passed;
2. rendered pages generated;
3. automated visual heuristics passed;
4. **human visual review recorded** — only `scripts/record_human_review.py`, run
   by a person, ever sets this.

## Honesty rules

Non-negotiable. The audit enforces what it can; the rest is on you.

- Never present an outline, skeleton, placeholder or partial artefact as final.
- Never claim all calculations were verified because a document was generated.
- Never mark a problem VERIFIED without the required evidence.
- Never state a page count before reading it from the generated PDF.
- Never claim visual inspection unless the evidence exists.
- Never silently copy or normalise an error in an official solution.
- Never hide unresolved assumptions or missing problem data.
- Never pad a document to reach a requested page count. Page targets are
  guidance; going outside the range with a stated reason is fine.
- Never overwrite the latest valid checkpoint with a less complete state.
- Never declare completion while any mandatory gate is false.

## Final report

Always state, separately and plainly: what was **verified with evidence**, what
was only **checked automatically**, what remains **unresolved**, and what received
**human review**. Give real counts, the actual page count read from each PDF, and
every discrepancy found against official solutions.

## Setup

Scripts are standard-library-only; optional packages add capability and are never
required. Run `python3 scripts/doctor.py --sources <dir> --work-dir <dir>` first —
it reports what is missing and what that costs. Never install packages globally.

Config: copy `config.example.yaml` into the study project and edit. Profiles:
`profiles/generic-stem.yaml`, `profiles/thermodynamics.yaml`,
`profiles/structures.yaml`. Examples in `examples/`. Portable prompt for agents
without skill support: `MASTER_PROMPT.md`.
