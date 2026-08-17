# Canonical content model

One model, two editions. Everything that must agree between the Korean-English
and English-only versions lives here and is generated, never retyped.

## Files

`WORK/canonical-content/` holds one pair per chapter:

```
CH-01.md      the prose, with ID-anchored blocks
CH-01.json    the structure: IDs, classifications, numbers, references
```

Both are plain text you can open and edit. That is deliberate: this is the master
copy, and it must stay editable years after the agent that wrote it is gone.

## ID anchors

Stable identifiers are marked in the Markdown with HTML comments, so the file
stays readable and renders normally everywhere:

```markdown
<!-- id: CH-01 kind: chapter -->
# Chapter 1 — Steady-flow energy balance

<!-- id: SEC-01-01 kind: section -->
## 1.1 Control volume selection

<!-- id: EQ-01-01 kind: formula -->
Qdot - Wdot = mdot (h2 - h1)
<!-- end: EQ-01-01 -->
<!-- end: SEC-01-01 -->

<!-- id: WE-01-01 kind: worked_example -->
### Worked example 1.1
...
<!-- end: WE-01-01 -->
<!-- end: CH-01 -->
```

Blocks nest. Every opened block must be closed, IDs must be unique within a file,
and the parser (`_lib.parse_blocks`) rejects unbalanced or duplicated markers —
so a broken anchor is caught immediately rather than corrupting a later parity
check.

## ID formats

| Kind | Pattern | Example |
|------|---------|---------|
| chapter | `CH-NN` | `CH-01` |
| section | `SEC-NN-NN` | `SEC-01-02` |
| concept | `CON-NN-NN` | `CON-01-01` |
| formula | `EQ-NN-NN` | `EQ-01-01` |
| derivation | `DRV-NN-NN` | `DRV-03-01` |
| figure | `FIG-NN-NN` | `FIG-02-01` |
| worked example | `WE-NN-NN` | `WE-01-01` |
| marking point | `MP-NN-NN` | `MP-01-03` |
| common error | `ERR-NN-NN` | `ERR-01-02` |

IDs are permanent. Renumbering a chapter breaks every verification record that
cites it, and the audit will report those records as pointing at content that no
longer exists — which is the correct outcome, but an avoidable one.

## The sidecar

`CH-01.json` conforms to `schemas/canonical-chapter.schema.json`:

```json
{
  "schema_version": 1,
  "chapter_id": "CH-01",
  "title_en": "Steady-flow energy balance",
  "title_ko": "정상유동 에너지 수지",
  "learning_objectives": ["Apply the SFEE to a turbine."],
  "sections": [{"section_id": "SEC-01-01", "title_en": "...", "title_ko": "..."}],
  "formulas": [{"equation_id": "EQ-01-01", "classification": "DS",
                "datasheet_source_id": "SRC-002", "statement": "..."}],
  "derivations": [{"derivation_id": "DRV-01-01", "expected_from_memory": true,
                   "result_equation_id": "EQ-01-01"}],
  "figures": [{"figure_id": "FIG-01-01", "caption_en": "...", "caption_ko": "..."}],
  "worked_examples": [{"example_id": "WE-01-01", "title_en": "...",
                       "past_paper_reference": "2023 Q2(b)",
                       "numerical_results": [{"label": "Wdot", "value": "1400", "unit": "kW"}]}],
  "exam_triggers": ["calculate the work", "comment on"],
  "past_paper_links": [{"source_id": "SRC-021", "question": "Q2(b)", "year": 2023}],
  "marking_points": [{"marking_point_id": "MP-01-01", "statement": "...", "marks": 2}],
  "common_errors": [{"error_id": "ERR-01-01", "statement": "..."}],
  "source_references": [{"source_id": "SRC-001", "pages": "12-18"}]
}
```

Every ID declared in the sidecar must exist as an anchored block in the Markdown.
`final_audit.py` checks this and reports any declaration with no matching block.

`source_references` needs at least one entry — a chapter grounded in nothing is
not source-grounded.

## What must match across editions

Generated from the model, therefore identical in both:

- chapter, section, equation, worked-example and figure IDs;
- the order those IDs appear in;
- numerical results;
- assumptions;
- verification status;
- source references.

Free to differ: prose, sentence count, page count, heading wording, and how much
explanation each concept gets.

`check_parity.py` compares IDs, kinds and ordering, and with `--canonical` also
checks that every declared numerical result appears verbatim in both editions.

## `numerical_results`

List every number a reader might copy into an exam answer. Two reasons: the
parity check verifies the same value reaches both editions, and a divergence here
is the single most damaging error the pack can contain — a student who memorises
1400 kW from one edition and 1750 kW from the other has been actively harmed.

Store values as strings when formatting matters (`"1.40e3"`, `"1400"`), so the
parity check compares what the reader actually sees.

## Editing later

The model is text; edit it. But a worked example that has been verified carries a
content hash in its verification record, and editing the block invalidates that
record — `verify_evidence.py` reports it as `STALE` and the final audit fails.

That is the intended behaviour, not an obstacle. After editing, re-verify the
example and update the record's hash. See `problem-verification.md`.
