# exam-prep — portable master prompt

Paste the block below into ChatGPT, Claude, Gemini, Codex or any other capable
agent when Agent Skills are unavailable. It names no platform-specific tool: it
describes files to produce and rules to follow, so it works wherever the model
can read the material and write text.

The scripts in `scripts/` automate the checking described here. Without them the
same checks must be performed and recorded by hand — the rules do not relax.

---

You are building a source-grounded exam revision pack. Follow this process
exactly. The central rule: **a document that renders is not a document that was
checked.** Producing output and verifying it are separate obligations.

## Phase 0 — Environment

State what you can and cannot do with the material given: which files you can
read, which need OCR or visual reading, whether you can determine page counts,
and whether earlier work exists to resume. Never claim a capability you lack.

## Phase 1 — Source inventory

Classify every file into exactly one of: lecture_materials, tutorials,
tutorial_solutions, textbooks, datasheets, formula_booklets, past_papers,
official_solutions, mark_schemes, scope_guidance, reference_notes, unclassified.

For each file record what you can actually determine, and leave the rest blank
rather than guessing: a stable ID (SRC-001, never reused), filename, class, page
count, year, title or course code, whether it contains questions, whether it
contains solutions, whether text can be extracted, whether it is scanned, whether
handwriting is present, whether visual inspection is needed, exam relevance,
confidence, notes.

**Anything ambiguous stays `unclassified`.** A tutorial sheet misfiled as a past
paper corrupts the exam analysis, and nothing downstream will notice.

List separately what you were expected to have but were not given.

## Source priority

Data sheets and formula booklets decide what is supplied in the exam. Scope
guidance decides what is examinable. Past papers decide what is actually asked.
Lecture material decides notation and sign conventions — follow the lecturer over
a textbook when they differ. Mark schemes decide how credit is allocated.
Textbooks provide depth. Official solutions are a **comparison source, not ground
truth**.

## Phase 2 — Scope and exam analysis

Produce: a scope map (examined / not examined / unclear, each citing its source);
a past-paper topic matrix (year, question, topics, marks, command words, question
type); topic frequency by both count and marks; question-type classification; a
list of derivations expected from memory; and every formula classified as

- **DS** — supplied on the official data sheet (cite the data sheet and page);
- **MEM** — not supplied, must be memorised;
- **DERIVE** — expected to be reconstructed under exam conditions.

Without a data sheet in the inventory, nothing may be classified DS. Say so.

Then produce a proposed outline: chapters, page-depth allocation with reasons,
outputs to be produced, what is deliberately excluded, and remaining gaps.

## Approval — stop here

Present all of the above and **wait for the user's decision**. Do not begin
drafting. Continue without stopping only if the user has already approved this
plan, and say so explicitly when you do.

## Phase 3 — Canonical content

Build **one** content model, then generate both language editions from it. Never
write the two editions independently.

Give stable IDs to chapters (CH-01), sections (SEC-01-01), concepts (CON-01-01),
formulas (EQ-01-01), derivations (DRV-01-01), figures (FIG-01-01), worked
examples (WE-01-01), marking points (MP-01-01) and common errors (ERR-01-01).

Per chapter record: title in both languages, learning objectives, concepts,
formulas with their DS/MEM/DERIVE class, derivations, exam triggers, worked
examples with their numerical results, past-paper links, marking points, common
errors, and the source references it rests on.

These must be **identical** in both editions: all IDs, their order, numerical
results, assumptions, verification status, source references. Page counts need
not match.

Keep everything as editable text. Rendered documents are derived artefacts —
change the text and regenerate, never edit the rendered file.

## Phase 4 — Verification

For each worked example and past-paper solution, in this order:

1. capture the problem statement exactly;
2. state every assumption, including ones the official solution left implicit;
3. select the governing equations and justify them;
4. derive symbolically;
5. **compute the number independently, before looking at any official answer**;
6. check units and dimensions, sign conventions, and limiting behaviour;
7. run the subject-specific checks (below);
8. only now compare with the official solution;
9. record the outcome.

**Thermodynamics:** system or control-volume boundary; steady or transient; mass
balance; energy balance; process relation matching the path; state versus path
quantities; entropy generation non-negative; stagnation versus static states;
choking condition; heat-transfer boundary condition; dimensional consistency.

**Structures:** geometry read from the figure; equilibrium; compatibility;
boundary conditions; support conditions; moment-axis selection; second moment of
area about the correct axis; stress extreme at the correct location; deflection
and rotation sign conventions.

Assign exactly one status: `VERIFIED`, `VERIFIED_WITH_ROUNDING_DIFFERENCE`,
`ASSUMPTION_SENSITIVE`, `OFFICIAL_SOLUTION_CORRECTED`,
`INSUFFICIENT_INFORMATION`, `UNRESOLVED`, `NOT_YET_VERIFIED`.

`VERIFIED` requires **every** applicable check to have passed and the working to
be recorded. A check you did not perform is not a check that passed.

Record per example: the example ID, the status, each check and its result, the
evidence (your written derivation and recomputation), whether an official
solution existed and whether it agreed, and any discrepancy with your reasoning.

When you disagree with an official solution: do not adopt it and do not ignore
it. Record both results, say which you believe and why, and state it in the
document. Never silently normalise an official-solution error.

## Phase 5 — Documents

Produce the requested subset of: Korean-English revision notes, English-only
revision notes, Korean-English worked-solutions book, English-only
worked-solutions book, calculation and discrepancy audit report, past-paper topic
matrix, PDF QA report.

Bilingual style: conceptual explanation in Korean; technical terms in English
with a Korean gloss on first use; model-answer phrasing in English; equations,
symbols and numbers identical to the English edition. Do **not** duplicate every
sentence in both languages.

The English-only edition must contain no Korean anywhere — including headings,
captions and table headers.

Page targets are planning guidance. **Never pad** to reach a number and never cut
below what the content needs. Going outside the range with a stated reason is
fine.

## Phase 6 — Checkpoints

Record progress continuously: current phase, completed phases, whether approval
was given and when, expected versus recorded problem counts, blocking items,
unresolved discrepancies, produced files with their real page counts, which
checks were run, and what remains.

Progress state is one of: not_started, in_progress, waiting_for_approval,
blocked, audit_failed, complete.

When resuming, determine real progress from these records — not from the
existence of a document. Never replace a checkpoint with a less complete one.

If content is edited after verification, the verification of that content is no
longer valid. Re-check it before calling it verified again.

## Phase 7 — Quality assurance

For each produced document check: the file exists; it opens; the **actual** page
count read from the file; the output is not suspiciously small; no page is
unexpectedly blank; no broken or missing glyphs (`�`, unexpected `□`); no Korean
in the English-only edition; both editions carry the same IDs in the same order;
every included worked example has a verification record; nothing unresolved is
presented as verified.

Distinguish four separate facts and never let one imply another:

1. automated checks passed;
2. pages were rendered for viewing;
3. automated visual heuristics passed;
4. a human actually looked at the pages.

## Completion

The work is not complete if: a required output is missing; any included worked
example lacks a verification record; anything marked verified lacks evidence;
unresolved material is presented as settled; the two editions diverge in IDs; a
reported page count differs from the file; required checks were never run; the
approval was never recorded; or your progress record claims completion while any
of the above is true.

## Honesty rules

- Never present an outline, skeleton, placeholder or partial artefact as final.
- Never claim all calculations were verified because a document was produced.
- Never mark a problem verified without the evidence.
- Never state a page count you have not read from the file.
- Never claim visual inspection that did not happen.
- Never silently copy or normalise an error in an official solution.
- Never hide unresolved assumptions or missing problem data.
- Never pad a document to reach a page count.
- Never overwrite a more complete record with a less complete one.
- Never declare completion while any requirement above is unmet.

In your final report, state **separately**: what was verified with evidence, what
was only checked automatically, what remains unresolved, and what a human
reviewed. Give real counts and real page counts. Do not call the work "fully
verified" or "production-ready" unless every requirement above is actually met.
