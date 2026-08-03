# Example — the final audit and what to report

## Running Phase 7

```
python3 scripts/pdf_preflight.py output/notes-en.pdf --work-dir .agent-work/exam-prep
python3 scripts/check_english_only.py .agent-work/exam-prep/editions/english output/notes-en.pdf
python3 scripts/check_parity.py \
    --english   .agent-work/exam-prep/editions/english \
    --bilingual .agent-work/exam-prep/editions/bilingual \
    --canonical .agent-work/exam-prep/canonical-content
python3 scripts/render_contact_sheet.py output/notes-en.pdf --work-dir .agent-work/exam-prep
python3 scripts/final_audit.py --work-dir .agent-work/exam-prep --write
```

Take the page count from preflight's output. Do not write it from the outline's
estimate — that is exactly the number the audit will catch.

```
[PASS] pdf_preflight
  - notes-en.pdf: 118 page(s), 4821904 bytes (read with pymupdf)
  ! notes-en.pdf: page(s) 47, 92 have fewer than 12 visible characters —
    possibly blank. This is a heuristic: full-page figures look the same.
    A human must confirm.
```

Pages 47 and 92 are full-page T-s diagrams. The heuristic cannot know that, so it
stays a warning for a human, and the answer goes in the QA report — not silently
dismissed.

## A failing audit

```
[FAIL] final_audit — .agent-work/exam-prep
  ok   sources_inventoried: 31 source(s) inventoried
  ok   outline_approved: approved by user at 2026-01-15T09:12:00+00:00
  ok   canonical_content_complete: 41 worked example(s) declared
  ok   all_examples_have_records: every worked example has a record
  FAIL no_unresolved_presented_as_verified: 3 example(s) are still unresolved and
       must not appear as verified: WE-05-02, WE-07-01, WE-07-03
  ok   no_stale_verification_records: no record was invalidated by a later edit
  ok   verification_evidence_complete: all settled records carry the required checks and evidence
  ok   language_editions_in_parity: canonical IDs match across editions
  ok   required_artifacts_present: 4 artefact(s) present
  ok   pdf_preflight_executed: executed at 2026-02-02T11:40:00+00:00
  FAIL page_counts_match_actual: notes-en.pdf: reported 120 pages, file has 118
  warn human_visual_review_recorded (advisory): no human has recorded a visual review
  FAIL progress_matches_reality: progress says 'complete' but 3 gate(s) fail
```

Three real problems. Fix them; do not describe the work as done.

1. **Three unresolved examples.** Either resolve them, or mark them clearly in
   both editions as unresolved and remove them from the settled count. Leaving
   them presented as checked is the failure the gate names.
2. **Page count.** 120 came from the outline's estimate. The file has 118. Fix
   `reported_page_count` to what preflight read.
3. **`progress_matches_reality`.** The checkpoint said `complete` while gates
   failed. Set the state back to `in_progress` or `audit_failed`.

## Human review

```
python3 scripts/record_human_review.py --work-dir .agent-work/exam-prep \
    --reviewer "지수" --pages "all 118 pages" \
    --note "p.47 and p.92 confirmed as full-page T-s diagrams, not blank"
```

Nothing else sets this. If nobody looked, the report says nobody looked.

## The final report

After the audit passes, report the four categories separately:

---

**Verified with evidence — 38 of 41 worked examples.** Each has a complete set of
the thermodynamics profile's required checks, at least one evidence artefact, and
a content hash matching the current text. "Verified" here means the verification
work was performed, recorded and is still valid — it is not an independent
guarantee that every answer is correct.

**Checked automatically only.** PDF preflight passed on all 4 documents (118 /
124 / 96 / 101 pages, each read from the file). Canonical ID parity passed across
both editions. The English edition contains no Hangul. Pages 47 and 92 tripped
the blank-page heuristic and were confirmed as full-page figures by a human.
Per-problem hooks ran for 31 of 38 settled examples; the other 7 rely on recorded
manual recomputation.

**Unresolved — 3 examples, plus 2 open discrepancies.**
- `WE-05-02` ASSUMPTION_SENSITIVE: the question does not fix the compressor
  isentropic efficiency; the answer is given for η = 0.85 and this is stated on
  the page.
- `WE-07-01` INSUFFICIENT_INFORMATION: the pressure-ratio figure in the 2021
  paper scan is illegible. A readable copy would settle it.
- `WE-07-03` UNRESOLVED: our result differs from the official solution by 8% and
  neither position is clearly right (`DISC-006`).
- `DISC-004`: the official solution to `WE-03-02` omits the parallel-axis term.
  We are confident it is wrong; the document says so and shows both results.
- `DISC-006`: as `WE-07-03`.

**Human review.** 지수 reviewed all 118 pages of the English notes on 2026-02-02.
The other three documents have not been visually reviewed by anyone.

**Also worth knowing.** The 2023 and 2024 past papers were not supplied, so
recent-topic weighting rests on 2019–2022 only. The pack runs 118 pages against a
preferred 70–130 — within range, no padding was added.

---

## What "pass" does not mean

A passing audit means the evidence exists, is complete, and is consistent. It
does not mean the mathematics is right, the explanations are good, or the scope
analysis was correct. Say what was checked, and let the reader judge the rest.
