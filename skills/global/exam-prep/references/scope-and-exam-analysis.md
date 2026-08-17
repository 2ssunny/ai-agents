# Scope and exam analysis (Phase 2)

Everything here is produced **before** any content is drafted, and the outline it
ends with is what the user approves.

## 1. Scope map — `scope-map.json`

Three buckets, each entry citing the source that settles it:

```json
{
  "schema_version": 1,
  "examined": [
    {"topic": "Steady-flow energy equation", "source_id": "SRC-014",
     "evidence": "syllabus L3-L5; appears in 4 of 5 past papers"}
  ],
  "not_examined": [
    {"topic": "Combustion stoichiometry", "source_id": "SRC-014",
     "evidence": "syllabus marks as background, no past-paper occurrence"}
  ],
  "unclear": [
    {"topic": "Exergy", "source_id": null,
     "evidence": "lectured in week 9 but absent from the syllabus and all supplied papers",
     "recommendation": "cover briefly; ask the lecturer"}
  ]
}
```

`unclear` is a real bucket. Do not resolve it by guessing — surface it at the
approval stop and let the user decide.

## 2. Past-paper topic matrix — `exam-topic-matrix.json`

One row per past-paper question:

```json
{
  "schema_version": 1,
  "questions": [
    {"source_id": "SRC-021", "year": 2023, "question": "Q2(b)",
     "topics": ["steady-flow energy equation", "isentropic efficiency"],
     "marks": 12,
     "command_words": ["calculate", "comment on"],
     "question_type": "numerical",
     "requires_derivation": false,
     "formulas_used": ["EQ-01-01", "EQ-03-02"]}
  ]
}
```

This is the evidence base for everything below, so it must be built from the
papers themselves, not from memory of what the subject usually asks.

## 3. Topic frequency

Count occurrences and marks per topic across all papers. Report both — a topic
worth 20 marks once matters differently from one worth 4 marks every year.

Frequency informs page-depth allocation. It does not dictate it: a topic that is
rare but hard still needs the space that makes it learnable.

## 4. Question-type classification

Classify each question as numerical, derivation, explanation, sketch/diagram,
design/selection, or mixed. Record the command words verbatim — profiles list the
subject's vocabulary in `exam_trigger_vocabulary`, and a course's habitual
phrasing is a strong signal of what the answer must contain.

Note which derivations recur. Those are the ones expected from memory.

## 5. Formula classification — DS / MEM / DERIVE

Every formula that will appear in the pack gets exactly one class:

| Class | Meaning | Evidence required |
|-------|---------|-------------------|
| `DS` | Supplied on the official data sheet | The `source_id` of the data sheet, and the page it is on |
| `MEM` | Not supplied; must be memorised | Absence from the data sheet, plus its use in a past paper |
| `DERIVE` | Expected to be reconstructed under exam conditions | A past paper asking for the derivation, or lecture material presenting it as derivable |

Without a data sheet in the manifest, **nothing may be classified DS**. Say so in
the missing-source report and classify conservatively as MEM — telling a student a
formula will be supplied when it will not is the worst error this pack can make.

Record the classification in each chapter sidecar's `formulas` array, and print
it beside the formula in both editions.

## 6. Derivations expected from memory

List them explicitly. For each: the result equation ID, where it was examined, and
how long the full derivation runs. These drive Phase 3's depth decisions — a
derivation a student must reproduce needs every step, not a summary.

## 7. Proposed outline — `proposed-outline.md`

The document the user approves. It contains:

- the chapter list with IDs and one-line scope statements;
- page-depth allocation per chapter, with the reason (frequency, marks,
  difficulty, derivation load);
- which of the seven output types will be produced;
- the DS/MEM/DERIVE table;
- the derivations expected from memory;
- what is deliberately excluded, and why;
- gaps: topics with no source coverage, and what is needed to close them.

State the page total this implies and check it against the profile's
`page_targets`. If it falls outside the preferred range, say so and give the
reason. Do not adjust the content to hit a number — see `document-style.md`.

## 8. Stop

Present all of the above and wait. This is the approval boundary described in
`workflow.md`. Record the outcome in `progress.json` before drafting anything.
