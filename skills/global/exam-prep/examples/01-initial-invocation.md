# Example — starting a new project

What the user says, and what the agent does up to the approval stop.

## The request

> 열역학 시험 대비 노트 만들어줘. `sources/`에 강의노트, 튜토리얼이랑 답안,
> 데이터시트, 2019~2022 기출이랑 공식 해설 다 들어있어. 한국어 설명 + 영어
> 용어 버전이랑 영어 전용 버전 둘 다 필요해.

Combines course material with a study deliverable, so `exam-prep` activates.

## Phase 0

```
python3 .claude/skills/exam-prep/scripts/doctor.py \
    --sources sources --output output --work-dir .agent-work/exam-prep
```

```
[PASS] doctor
  - Python 3.11.15
  - PyYAML: available (6.0.1)
  - pymupdf: available (1.24.9)
  - 31 candidate source file(s) under sources
  - all 31 PDF(s) have an extractable text layer
  - no previous state: .agent-work/exam-prep does not exist yet (this is a fresh project)
```

Report the environment honestly before starting. If a PDF reader had been
missing, say what that costs rather than proceeding as if it did not matter.

## Phase 1

```
python3 .claude/skills/exam-prep/scripts/inventory_sources.py \
    --sources sources --work-dir .agent-work/exam-prep
python3 .claude/skills/exam-prep/scripts/validate_manifest.py \
    --work-dir .agent-work/exam-prep
```

```
[PASS] inventory_sources
  - 31 file(s) inventoried (0 kept from the existing manifest)
  ! 4 file(s) left unclassified — classify them by hand before Phase 2:
    week07-supplementary.pdf, notes-scan-3.pdf, handout-b.pdf, MECH2001-extra.pdf
```

Open the four, decide what they are, and correct the manifest by hand. Do not
let the heuristic's guess stand in for a decision — the classifier deliberately
refuses to choose when two classes score close together.

Then fill in what the script could not read: years, titles, exam relevance.

## Phase 2

Produce the scope map, topic matrix, frequency analysis, question-type
classification and the outline. Then **stop**, and present:

---

**Source inventory** — 31 files: 12 lecture, 6 tutorials, 6 tutorial solutions,
1 data sheet, 4 past papers (2019–2022), 2 official solutions.

**Missing** — 2023 and 2024 papers were not supplied. Impact:
`degrades_coverage`. The two most recent papers usually signal where the
examiner is heading, so recent-topic weighting is less reliable than it looks.

**Scope** — 9 topics examined, 2 explicitly out of scope, 1 unclear: exergy was
lectured in week 9 but appears in no supplied paper and is absent from the
syllabus. **Your call** — cover it briefly, or leave it out?

**Topic frequency** — steady-flow energy equation in 4/4 papers (avg 18 marks);
entropy generation 4/4 (14); gas cycles 3/4 (16); psychrometrics 1/4 (8).

**Formula classification** — 34 formulas: 19 DS (on the supplied data sheet,
SRC-007), 9 MEM, 6 DERIVE.

**Derivations expected from memory** — 6, listed with the papers that asked for
them.

**Proposed outline** — 8 chapters, ~96 pages, allocated by frequency × marks ×
difficulty. Within the profile's preferred 70–130 range.

**Outputs** — bilingual notes, English notes, both worked-solutions books, audit
report, topic matrix, PDF QA report.

Approve, or tell me what to change?

---

Now wait. Do not begin Phase 3.

## After approval

Record it before drafting:

```json
"approval": {
  "outline_approved": true,
  "approved_at": "2026-01-15T09:12:00+00:00",
  "approved_by": "user",
  "approval_note": "approved; include exergy briefly; more depth on gas cycles"
}
```

An approval that was given but never recorded fails the final audit.
