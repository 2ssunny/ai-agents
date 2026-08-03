# Document style

Text-based style specification. There are no binary template files in this skill
— a `.docx` template that nobody can open in a diff is not maintainable, and a
placeholder one exists only to make a directory listing look complete.

Apply these as the renderer's settings, whether you generate through
`python-docx`, Pandoc, LaTeX or Markdown-to-PDF.

## The seven outputs

| # | Output | Language | Format |
|---|--------|----------|--------|
| 1 | Revision notes | Korean explanation, English terms and exam wording | DOCX/PDF |
| 2 | Revision notes | English only | DOCX/PDF |
| 3 | Worked-solutions book | Korean-English | DOCX/PDF |
| 4 | Worked-solutions book | English only | DOCX/PDF |
| 5 | Calculation and discrepancy audit report | English | MD/PDF |
| 6 | Past-paper topic matrix | English | MD/CSV/PDF |
| 7 | Final PDF QA report | English | MD/JSON |

Produce those the config's `outputs` list asks for. Outputs 5–7 are the honesty
record and should be produced whenever 1–4 are.

## Page geometry

| Setting | Value |
|---------|-------|
| Page size | A4 (210 × 297 mm) |
| Margins | 20 mm top/bottom, 22 mm inner, 18 mm outer |
| Body text | 10.5 pt, 1.30 line spacing |
| Body font (English) | a serif face with a full maths range — Charter, Source Serif, Latin Modern |
| Body font (Korean) | a Hangul face that covers the full syllabary — Noto Sans KR, Pretendard, Malgun Gothic |
| Monospace | any face with a clear 0/O and 1/l distinction |

**Font embedding is not optional.** An unembedded Hangul face renders as `□` on
another machine, and `pdf_preflight.py` reports those as broken glyphs — which is
the check working, but a wasted render cycle. Embed subsets of every face used.

## Headings and numbering

| Level | Style |
|-------|-------|
| Chapter | 18 pt bold, page break before, numbered `1.` |
| Section | 13 pt bold, numbered `1.1` |
| Subsection | 11 pt bold, numbered `1.1.1` |
| Worked example | 11 pt bold, `Worked example 1.1`, boxed or rule-separated |

Numbering must match the canonical IDs: `CH-01` renders as chapter 1, `SEC-01-02`
as section 1.2, `WE-01-01` as worked example 1.1. A reader who finds the audit
report referring to `WE-03-02` must be able to find it in the document.

## Equations

- Display equations centred, numbered on the right as `(1.1)`, matching `EQ-01-01`.
- Every equation carries its DS/MEM/DERIVE class as a right-margin tag or a
  bracketed suffix. This is the single most useful thing on the page during
  revision — the student needs to know what they must memorise.
- Define each symbol on first use in a chapter, with units.
- Keep the notation the course uses, even where a textbook differs.

## Worked examples

Fixed structure, so the reader learns where to look:

1. **Question** — restated, with the past-paper reference if it has one.
2. **Assumptions** — listed, not buried in prose.
3. **Method** — governing equations and why they apply.
4. **Working** — symbolic first, numbers second.
5. **Answer** — stated with units, visually distinct.
6. **Marking points** — what earns credit, with marks where the mark scheme says.
7. **Common errors** — what loses it.
8. **Verification note** — the status, and any discrepancy with the official
   solution.

Item 8 is not optional. An example whose status is not `VERIFIED` must say so on
the page, in the reader's language.

## Figures

Every figure gets an ID, a caption, and a source reference. A figure redrawn from
a source says so; a figure that could not be reproduced is described in words
rather than silently omitted.

Never insert a figure placeholder. An empty box captioned "figure to follow" is a
skeleton presented as a finished document.

## Page targets

The profile's `page_targets` are **planning guidance**, not a completion
criterion:

| Field | Meaning |
|-------|---------|
| `minimum_pages` | Below this, coverage is probably too thin — check, do not pad |
| `preferred_min_pages` / `preferred_max_pages` | The range the depth allocation aims at |
| `maximum_advisory_pages` | Beyond this the pack is likely unusable for revision |
| `allow_out_of_range_with_explanation` | Whether falling outside is acceptable with a stated reason |

Rules:

- **Never pad.** Not with restated definitions, not with whitespace, not with
  duplicated examples, not by splitting one worked example into three. Padding to
  hit a number makes the document worse and the count meaningless.
- **Never trim below what the content needs** to fit a maximum. Say it ran long.
- Going outside the range is fine when the reason is stated in the final report —
  "the 2023 and 2024 papers added two topics, so this runs 140 pages against a
  preferred 130".
- The page count in any report comes from `pdf_preflight.py` reading the file.
  Never from an estimate, a plan, or the previous run.

## Cross-references

Reference by canonical ID, resolved to a human-readable label at render time:
`see Worked example 3.2` links to the `WE-03-02` anchor. Both editions must
resolve the same set of references — a link that works in one edition and dangles
in the other is a parity failure the ID check will catch.
