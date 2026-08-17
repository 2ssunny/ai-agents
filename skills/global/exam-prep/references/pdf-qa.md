# PDF and document QA

## Four separate facts

The central distinction of this phase. None of these implies any other, and they
are stored as four independent fields in `progress.visual_review`:

| Fact | Set by | Means |
|------|--------|-------|
| `automated_preflight_passed` | `pdf_preflight.py` | The file is structurally sound: readable, right page count, no broken glyphs |
| `rendered_pages_generated` | `render_contact_sheet.py` | Page images exist, so a human *could* look |
| `automated_visual_heuristics_passed` | `pdf_preflight.py` | No page tripped the blank-page heuristic |
| `human_visual_review_recorded` | `record_human_review.py`, run by a person | Someone actually looked |

Generating a contact sheet is not review. It makes review possible. The contact
sheet itself carries that warning in its header, because a screenshot of a
contact sheet is easily mistaken for evidence of inspection.

`final_audit.py` treats human review as advisory by default and mandatory with
`--require-human-review`. Either way, the audit's summary lists what was confirmed
by script alone, so the final report can state it accurately.

## Preflight

```
python3 scripts/pdf_preflight.py output/notes-en.pdf \
    --expect-pages 118 --min-pages 40 --work-dir WORK
```

Checks, in order:

1. **File exists.** A missing artefact is a failure, not a warning.
2. **PDF is readable.** If no reader is installed, the result is SKIPPED with exit
   code 3 — never a pass.
3. **Page count read from the file.** With PyMuPDF or pypdf, from the page tree.
   Without either, a stdlib fallback parses the raw page tree and returns a count
   **only when `/Count` and the number of `/Type /Page` objects agree**; on a
   compressed PDF it returns nothing rather than a plausible wrong number.
4. **Reported count matches.** `--expect-pages` fails when the number you were
   about to report differs from the file's. This is the check that stops a page
   count being quoted from a plan.
5. **Size per page.** Below 400 bytes/page the output is almost certainly
   truncated or blank.
6. **Blank pages.** A page with fewer than 12 visible characters is flagged. This
   is a **heuristic, not proof** — a full-page figure looks identical to a blank
   page from the text layer, so it is a warning asking for a human look, never a
   failure.
7. **Broken glyphs.** `�` or unexpected `□` means a font failed to embed. This is
   a failure: it will render wrong on the reader's machine too.

Preflight also writes a text sidecar to `WORK/pdf-text/<name>.txt`, one marked
section per page, so the rendered output can be searched and diffed later without
re-parsing the PDF.

## Hangul in the English edition

```
python3 scripts/check_english_only.py WORK/editions/english
python3 scripts/check_english_only.py output/notes-en.pdf
```

Run it on both the text source and the rendered PDF. The source is where you fix
it; the PDF catches anything the renderer injected — a template header, a
hard-coded caption, a font fallback.

On a PDF with no reader installed the file is reported as not scanned, and the
result says so rather than passing.

## Parity

```
python3 scripts/check_parity.py --english WORK/editions/english \
    --bilingual WORK/editions/bilingual --canonical WORK/canonical-content
```

Compares canonical IDs, their kinds and their order across the two editions, and
with `--canonical` verifies every declared numerical result appears verbatim in
both. Runs on the **text sources**, not the PDFs: a PDF cannot be diffed
meaningfully, and a fix applied to a PDF would not survive the next render.

## Rendering

```
python3 scripts/render_contact_sheet.py output/notes-en.pdf --work-dir WORK
```

Writes `page-0001.png` … under `WORK/rendered-pages/<stem>/` plus a
`contact-sheet.html` referencing them. HTML rather than a montage image so no
image-processing dependency is needed and the sheet stays a text artefact.

Needs PyMuPDF. Without it: SKIPPED, exit 3, no pages, and
`rendered_pages_generated` stays false.

## Human review

After a person has actually looked:

```
python3 scripts/record_human_review.py --work-dir WORK \
    --reviewer "<name>" --pages "all 118 pages" \
    --note "fixed a clipped figure on p.47"
```

The script refuses to record a review when no rendered pages exist — there would
have been nothing to look at. It records who, when, and what they covered. Partial
review is fine and should be recorded honestly: `"pp. 1-40 and 95-118 (spot
check)"` is useful; claiming all 118 when 40 were checked is not.

Nothing else in this skill sets `human_visual_review_recorded`. No agent may set
it on a person's behalf.

## The QA report

Output 7 records, for each document: the actual page count and where it came
from, which checks ran, which were skipped and why, warnings that a human must
resolve (possibly-blank pages), and the human review status.

Write it from the scripts' `--json` output rather than from memory. Every number
in it should be traceable to a command that produced it.
