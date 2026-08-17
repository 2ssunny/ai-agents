# Example — continuing on an outline the user already approved

The approval stop exists so the user controls the plan, not so it is asked twice.
When the plan is already settled, skip the stop — but never skip the record.

## When this applies

- the user approved the outline in an earlier session and the approval is already
  in `progress.json`;
- the user says up front "계획은 이미 정했으니까 바로 진행해";
- the project config sets `approval.continue_without_approval: true`.

It does **not** apply when the outline changed materially since approval. New
chapters, a different page allocation or a changed output set need a fresh
decision — say so and stop.

## Config

```yaml
approval:
  continue_without_approval: true
  approved_by: user
  approved_at: 2026-01-15T09:12:00+00:00
  approval_note: >
    Outline approved in the 2026-01-15 session: 8 chapters, ~96 pages,
    include exergy briefly, extra depth on gas cycles.
```

## What the agent does

1. Read the config and confirm the approval fields are populated. A
   `continue_without_approval: true` with no `approved_by` and no
   `approved_at` is not an approval — stop and ask.
2. Copy the recorded approval into `progress.json`:

```json
"approval": {
  "outline_approved": true,
  "approved_at": "2026-01-15T09:12:00+00:00",
  "approved_by": "user",
  "approval_note": "pre-approved via config; outline unchanged since 2026-01-15"
}
```

3. Still produce the Phase 2 artefacts — scope map, topic matrix,
   `proposed-outline.md`. They are inputs to Phase 3, not just a proposal to
   show. Skipping them leaves the audit with nothing to check the content
   against.
4. State briefly what is being built before starting, so the user can interrupt:

> 승인된 계획대로 8장, 96쪽 목표로 바로 Phase 3 들어갈게. exergy는 짧게,
> gas cycle은 깊게. 다르면 지금 말해줘.

5. Proceed to Phase 3.

## What still stops the work

`continue_without_approval` waives the *approval* stop. It does not waive
anything else:

- a `blocking` missing source still puts the project in `blocked` and needs the
  user;
- an unclear scope item still needs a decision;
- a source that cannot be read is still reported, not worked around;
- the final audit still requires the recorded approval and every other gate.

## Verifying the record took

```
python3 scripts/validate_state.py --work-dir .agent-work/exam-prep
```

```
[PASS] validate_state
  - progress: .agent-work/exam-prep/progress.json
```

If the approval had been missing while the phase had moved on, this fails:

```
  x current_phase is 'phase3_canonical_content' but approval.outline_approved is
    false — drafting may not begin before the outline is approved
```
