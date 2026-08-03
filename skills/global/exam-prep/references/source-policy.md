# Source policy

How input material is classified, trusted and cited.

## The twelve classes

| Class | What belongs here |
|-------|-------------------|
| `lecture_materials` | Slides, handouts, lecture notes issued by the course |
| `tutorials` | Problem sheets, exercise sets, seminar questions — questions only |
| `tutorial_solutions` | Worked answers to those sheets |
| `textbooks` | Books and book chapters |
| `datasheets` | The official data sheet supplied in the exam |
| `formula_booklets` | Formula sheets, equation booklets |
| `past_papers` | Previous examination papers |
| `official_solutions` | Model answers to past papers |
| `mark_schemes` | Marking guidance, examiner reports |
| `scope_guidance` | Syllabus, learning outcomes, revision guidance, exam format notes |
| `reference_notes` | Summaries and reference material not issued by the course |
| `unclassified` | Anything whose role is not settled |

## Ambiguity stays ambiguous

A file whose role you cannot determine stays `unclassified` with `confidence:
low` and a note saying why. Do not guess.

The cost of guessing is asymmetric. A tutorial sheet misfiled as a past paper
corrupts the topic frequency analysis, which corrupts the page-depth allocation,
which corrupts the whole pack — and nothing downstream will notice. Twenty
unclassified files that a human sorts in five minutes cost nothing.

`inventory_sources.py` refuses to classify when two classes score within one
point of each other, and `validate_manifest.py` rejects `unclassified` combined
with `confidence: high` as self-contradictory.

## Source priority

When sources disagree, prefer in this order:

1. **`datasheets` and `formula_booklets`** for what is supplied in the exam. These
   are definitive: if a relation is on the data sheet it is DS, whatever a
   textbook implies.
2. **`scope_guidance`** for what is examinable. A topic absent from the syllabus
   is not examined however much lecture time it received.
3. **`past_papers`** for what is actually asked, and in what form.
4. **`lecture_materials`** for the notation, sign conventions and method the
   course expects. Where a textbook and the lecturer differ on convention, follow
   the lecturer — the exam is marked against the course.
5. **`mark_schemes`** for how credit is allocated.
6. **`official_solutions`** and **`tutorial_solutions`** as comparison sources —
   see below.
7. **`textbooks`** for depth, derivations and background.
8. **`reference_notes`** last, and only when nothing above covers the point.

Record which source settled each decision. Every canonical chapter carries
`source_references`, and the audit requires at least one.

## Official solutions are not ground truth

Model answers and tutorial solutions contain errors: arithmetic slips, stale
numbers from an earlier version of the question, assumptions applied without
being stated, and occasionally a wrong method that happens to reach the published
answer.

So: solve first, compare second. When your result differs, do not quietly adopt
theirs and do not quietly keep yours. Record it:

- write the discrepancy to `discrepancy-log.json` with both results and the
  reasoning;
- set `official_solution.agreement` to `differs` and link `discrepancy_id`;
- if you are confident the official solution is wrong, use status
  `OFFICIAL_SOLUTION_CORRECTED` and state plainly in the document that the
  published answer differs and why;
- if you cannot tell which is right, use `ASSUMPTION_SENSITIVE` or `UNRESOLVED`
  and say what would settle it.

`verify_evidence.py` rejects a `differs` verdict with no `discrepancy_id`, and
rejects `OFFICIAL_SOLUTION_CORRECTED` unless the disagreement is recorded.

## Scanned, handwritten and image-only material

Set `text_extractable: false` and `ocr_required: true` rather than silently
skipping the file. A source that cannot be read has not been read, and its topics
must appear in `missing_sources` if they matter.

Never cite a page you could not actually read.

## Missing material

Record what you were not given:

```json
{
  "description": "2023 and 2024 past papers (only 2019-2022 supplied)",
  "impact": "degrades_coverage",
  "affected_topics": ["transient conduction", "exergy"]
}
```

`impact` is `blocking` (cannot proceed honestly), `degrades_coverage` (proceed,
but say what is thin), or `cosmetic`. Blocking items belong in
`progress.blocking_items` and put the project in state `blocked`.

## Stable IDs

`source_id` is assigned once and never reused or renumbered. Canonical content,
verification records and the topic matrix all cite it. Re-running the inventory
preserves existing IDs; `--overwrite` discards them and should be used only on a
project with no canonical content yet.
