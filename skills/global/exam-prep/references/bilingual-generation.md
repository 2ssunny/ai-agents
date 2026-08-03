# Bilingual generation

Two editions, one model. This describes how the Korean-English edition differs
from the English-only one, and what must not differ.

## The bilingual style

The reader thinks in Korean and sits the exam in English. The edition should
match that: explanation in the language they reason in, terminology and answer
phrasing in the language they will write.

**Do not translate sentence by sentence.** A document that says everything twice
is twice as long, half as readable, and drifts out of sync the first time one
copy is edited.

Instead:

- **Conceptual explanation in Korean.** Why the control volume is drawn there,
  what the term physically means, where students go wrong.
- **Technical terms stay English**, with the Korean gloss on first use in a
  chapter: `control volume (검사체적)`. After that, English alone.
- **Model-answer phrasing in English**, verbatim as it should be written in the
  exam. This is what the marker reads.
- **Equations, symbols and numbers identical** to the English edition.
- **Command words in English** — `derive`, `show that`, `comment on` — because
  that is how the question will be worded.

A worked example in the bilingual edition:

```markdown
<!-- id: WE-01-01 kind: worked_example -->
### Worked example 1.1 — adiabatic turbine

터빈이 adiabatic이므로 Qdot = 0이고, steady flow라 축적항도 없다.
따라서 SFEE는 일 항과 엔탈피 차만 남는다.

**Model answer.** Assuming steady, adiabatic flow with negligible changes in
kinetic and potential energy, the steady-flow energy equation reduces to

Wdot = mdot (h1 - h2) = 2.0 × (3200 - 2500) = 1400 kW

핵심: adiabatic 가정을 답안에 반드시 명시해야 assumption 배점을 받는다.
<!-- end: WE-01-01 -->
```

Korean carries the reasoning; the model answer is exam-ready English; the number
is the same one the English edition prints.

## The English-only edition

Fully English, no Hangul anywhere — including headings, figure captions, table
headers and footnotes, which is where it usually leaks in.

```
python3 scripts/check_english_only.py WORK/editions/english
```

The check reports file, line and column for every Hangul run. Fix them in the
text source, never in the rendered PDF.

Korean glosses (`control volume (검사체적)`) belong only in the bilingual edition.
The English edition writes `control volume`.

## What must stay aligned

Both editions are generated from `canonical-content/`, so these are identical by
construction — and verified afterwards:

| Aligned | Free to differ |
|---------|----------------|
| chapter / section / equation / example / figure IDs | prose and its length |
| the order those IDs appear in | how much explanation a concept gets |
| numerical results | heading wording |
| assumptions | worked-example commentary |
| verification status | **page count** |
| source references | |

Page counts differing is expected: Korean prose is more compact than the English
equivalent for the same content, and the bilingual edition carries commentary the
English one does not. Do not pad either edition to match the other.

```
python3 scripts/check_parity.py --english WORK/editions/english \
    --bilingual WORK/editions/bilingual --canonical WORK/canonical-content
```

With `--canonical`, every value in a chapter sidecar's `numerical_results` must
appear verbatim in both editions. A number that reaches one edition and not the
other is the most damaging divergence possible and this is what catches it.

## Verification status must be visible in both

If an example is `ASSUMPTION_SENSITIVE`, both editions say so — in Korean in one,
in English in the other, but neither may present it as settled. The same applies
to `OFFICIAL_SOLUTION_CORRECTED`: both editions state that the published answer
differs and why.

Suggested markers, kept short so they survive translation:

| Status | English edition | Bilingual edition |
|--------|-----------------|-------------------|
| `VERIFIED` | (no marker) | (no marker) |
| `VERIFIED_WITH_ROUNDING_DIFFERENCE` | *rounding differs from the model answer* | *모범답안과 반올림 차이* |
| `ASSUMPTION_SENSITIVE` | *depends on the assumption below* | *아래 가정에 따라 달라짐* |
| `OFFICIAL_SOLUTION_CORRECTED` | *the published answer differs — see note* | *공식 해설과 다름 — 아래 설명 참고* |
| `INSUFFICIENT_INFORMATION` | *cannot be solved from the supplied data* | *제공된 자료만으로는 풀 수 없음* |
| `UNRESOLVED` | *unresolved* | *미해결* |

## Generation order

Generate the English edition first, then the bilingual one from the same model.
Working in that order makes it obvious when Korean has leaked into the English
edition, because it was never there to begin with.

Never generate the bilingual edition by translating the English one — that breaks
the single-model rule and reintroduces exactly the drift this design prevents.
