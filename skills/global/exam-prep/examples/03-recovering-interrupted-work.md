# Example — resuming interrupted work

A session ended mid-project. There is a PDF in `output/`. The project is **not**
finished, and this is how to establish that rather than assume either way.

## The request

> 저번에 하던 열역학 노트 이어서 진행해

## Step 1 — find the state, do not guess it

```
python3 .claude/skills/exam-prep/scripts/doctor.py --work-dir .agent-work/exam-prep
```

```
[PASS] doctor
  - previous run found: state='in_progress' phase='phase4_verification',
    12 solution record(s) on disk — resume rather than restart
```

## Step 2 — is the checkpoint internally consistent?

```
python3 .claude/skills/exam-prep/scripts/validate_state.py --work-dir .agent-work/exam-prep
```

```
[FAIL] validate_state
  x counts.records_present=14 but 12 record file(s) exist in solution-records/
```

The checkpoint was written before the last two records were saved, or those
records were lost. Establish which — read `tool_results`, check file times — then
correct the count to match what is actually on disk. Never adjust the disk to
match the claim.

## Step 3 — what is actually finished?

```
python3 .claude/skills/exam-prep/scripts/final_audit.py --work-dir .agent-work/exam-prep
```

```
[FAIL] final_audit — .agent-work/exam-prep
  ok   sources_inventoried: 31 source(s) inventoried
  ok   outline_approved: approved by user at 2026-01-15T09:12:00+00:00
  ok   canonical_content_complete: 41 worked example(s) declared
  FAIL all_examples_have_records: 29 example(s) without a record: WE-03-04, ...
  ok   no_unresolved_presented_as_verified: no unresolved item is included as settled
  ok   no_stale_verification_records: no record was invalidated by a later edit
  FAIL language_editions_in_parity: a bilingual artefact is declared but the
       bilingual/ edition source is missing
  FAIL pdf_preflight_executed: PDF preflight was never executed
  -- 12/41 examples have records; 12 settled, 0 unresolved, 0 stale
  -- no human visual review is recorded; do not describe the pages as inspected
```

**The PDF in `output/` proves nothing.** It was rendered from a partial draft
before verification started. 12 of 41 examples are done.

## Step 4 — report and continue

Report in one or two lines, then get on with it:

> 41개 예제 중 12개까지 검증 끝났고, phase 4 중간에 끊겼네. output/ PDF는 검증
> 전에 뽑은 초안이라 무시하면 돼. WE-03-04부터 이어서 갈게.

Do not restart from Phase 0. Do not re-inventory. Do not re-verify the 12
finished examples — their records are intact and their content hashes still
match.

## Step 5 — do not regress the checkpoint

```
cp .agent-work/exam-prep/progress.json .agent-work/exam-prep/progress.prev.json
# ... verify more examples, write the new checkpoint ...
python3 .claude/skills/exam-prep/scripts/validate_state.py \
    --work-dir .agent-work/exam-prep --against .agent-work/exam-prep/progress.prev.json
```

If a confused run tried to write a fresh blank state:

```
  x counts.settled_records would drop from 12 to 0 — never overwrite the latest
    valid checkpoint with a less complete state
  x phase 'phase3_canonical_content' was complete in the previous checkpoint and
    is not here
```

## If the content was edited between sessions

Someone fixed a typo in `CH-03.md` by hand. That is allowed — the text is the
master — but it invalidates the verification of anything inside the edited block:

```
python3 .claude/skills/exam-prep/scripts/verify_evidence.py --work-dir .agent-work/exam-prep
```

```
  x REC-009.json: STALE — WE-03-02 in canonical-content/CH-03.md was edited after
    verification (recorded 8f2a1c9d4e77…, current b41d09aa5c02…).
    Re-verify the problem or reset the record's status.
```

Re-check the problem, then update `content_hash.value` and `verified_at`. Do not
update the hash without re-checking — that turns the guard into a rubber stamp.
