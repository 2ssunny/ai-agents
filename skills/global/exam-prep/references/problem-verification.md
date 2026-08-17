# Problem verification

## What can and cannot be automated

No general-purpose script can verify arbitrary engineering coursework. Doing so
would require solving the problem, which requires understanding the geometry, the
physical setup, the conventions the course uses, and what the question is
actually asking. A tool claiming otherwise would produce false confidence exactly
where confidence is most expensive.

So the automation here is honest about its scope:

| Question | Answered by |
|----------|-------------|
| Is this answer correct? | A person or agent solving it. Not a script. |
| Was the solving work actually done and recorded? | `verify_evidence.py` |
| Does the evidence point at real artefacts? | `verify_evidence.py` |
| Did every check the subject demands get performed? | `verify_evidence.py` |
| Is this verification still valid after the text changed? | `verify_evidence.py` (content hash) |
| Does *this specific* number come out right? | A per-problem hook you write |

The script is named `verify_evidence.py`, not `verify_calculations.py`, because
that is what it does.

## The method

For each worked example, in this order. The order matters — comparing against the
official solution before solving contaminates the independent check.

1. **Capture the problem statement** exactly from the source. Transcription
   errors here invalidate everything downstream, and they are common with scanned
   papers.
2. **State every assumption**, including the ones the official solution used
   without saying so. If the problem is underdetermined without an assumption,
   that is a finding, not a gap to paper over.
3. **Select the governing equations** and say why they apply to this system.
4. **Derive symbolically** to an expression in the given quantities.
5. **Compute the number independently.** Do not look at the official answer yet.
6. **Run the profile's checks** — units, signs, limiting behaviour, and the
   subject-specific ones.
7. **Now compare** with the official solution.
8. **Record the outcome**, including disagreement.

## Statuses

| Status | When |
|--------|------|
| `VERIFIED` | Every required check passed; result agrees with the official solution, or no official solution exists and the independent work is sound |
| `VERIFIED_WITH_ROUNDING_DIFFERENCE` | Agrees to within rounding; the difference is explained |
| `ASSUMPTION_SENSITIVE` | The answer depends on an assumption the question does not fix; state the assumption and the answer under it |
| `OFFICIAL_SOLUTION_CORRECTED` | The official solution is wrong; the discrepancy is logged and the document says so |
| `INSUFFICIENT_INFORMATION` | The problem cannot be solved from what was supplied (illegible figure, missing data) |
| `UNRESOLVED` | Worked on, not settled |
| `NOT_YET_VERIFIED` | Not yet worked on |

The first, second and fourth are **settled**: they may appear in the pack as
checked. The rest are **unresolved** and must be labelled as such in the document
— `final_audit.py` fails if an unresolved example is present in a pack claiming
completion.

## Required checks

The subject profile lists them. A settled status needs every required check
present with result `pass`, or `not_applicable` **with a note saying why**. A
missing check is treated as not performed, never as passing.

`generic-stem` requires: problem statement captured, assumptions stated,
governing equations selected, symbolic derivation checked, numerical
recomputation, units and dimensions, sign conventions, limiting behaviour,
official solution compared, discrepancies recorded.

`thermodynamics` adds: system/control-volume boundary, steady or transient, mass
balance, energy balance, process relation, state versus path, dimensional
consistency. Optional but **required when they apply**: entropy generation,
stagnation versus static, choking condition, heat-transfer boundary condition.

`structures` adds: geometry interpretation, equilibrium, boundary conditions,
support conditions, moment-axis selection, second-moment-of-area orientation,
stress extreme location. Optional but required when they apply: compatibility
(statically indeterminate problems), deflection/rotation sign convention (any
reported displacement).

Promoting an optional check when it applies is a judgement the script cannot
make. Leaving out `compatibility` on an indeterminate frame is exactly the error
the profile exists to catch, and only you can catch it.

## The record

One JSON file per example in `WORK/solution-records/`, conforming to
`schemas/verification-record.schema.json`:

```json
{
  "schema_version": 1,
  "record_id": "REC-014",
  "example_id": "WE-03-02",
  "chapter_id": "CH-03",
  "profile_id": "structures",
  "status": "OFFICIAL_SOLUTION_CORRECTED",
  "checks": [
    {"check_id": "equilibrium", "result": "pass", "note": null},
    {"check_id": "second_moment_orientation", "result": "pass",
     "note": "bending about the strong axis; parallel-axis term for the flange offset"},
    {"check_id": "official_solution_compared", "result": "pass",
     "note": "model answer omits the parallel-axis term"}
  ],
  "evidence": [
    {"kind": "independent_recomputation",
     "path": "verification/WE-03-02-recompute.md",
     "description": "Section properties and bending stress recomputed from the figure.",
     "script_hook": "verification/WE-03-02-check.py"}
  ],
  "official_solution": {
    "available": true, "source_id": "SRC-031",
    "agreement": "differs", "discrepancy_id": "DISC-004"
  },
  "content_hash": {
    "algorithm": "sha256",
    "source_file": "canonical-content/CH-03.md",
    "block_id": "WE-03-02",
    "value": "<sha256 of the block body>"
  },
  "assumptions": ["Linear elastic", "Plane sections remain plane"],
  "unresolved_questions": [],
  "verified_at": "2026-01-15T14:20:00+00:00",
  "verified_by": "agent"
}
```

Evidence kinds `recorded_derivation`, `independent_recomputation` and
`verification_script` must carry a `path` that resolves to a real file relative to
`WORK`. The schema itself makes a settled status without evidence structurally
invalid, so this cannot be bypassed by skipping the script.

## Per-problem hooks

`script_hook` names a Python script run as `python <hook>` from `WORK`, when
`verify_evidence.py --run-hooks` is given. Exit 0 means the check passed.

This is where real numerical verification happens — one small script per problem,
written by whoever solved it, recomputing the answer a second way:

```python
"""Independent check of WE-03-02: bending stress at the extreme fibre."""
import sys

B, D, T = 100e-3, 200e-3, 12e-3          # m, from the figure
M = 45e3                                  # N·m
I = (B * D**3 - (B - 2 * T) * (D - 2 * T)**3) / 12
sigma = M * (D / 2) / I
expected = 71.2e6                         # Pa, from the recorded derivation

sys.exit(0 if abs(sigma - expected) / expected < 0.01 else 1)
```

Hooks are off by default because running them executes code from the working
directory. Turn them on deliberately.

## Staleness

The record stores the sha256 of the canonical block it verified. If that block is
later edited, the hash no longer matches and `verify_evidence.py` reports
`STALE`; `final_audit.py` fails.

This is what keeps the text editable without letting an edit silently inherit an
old verification. After changing verified content: re-check the problem, then
update `content_hash.value` and `verified_at`. Never update the hash without
re-checking — that converts the guard into a rubber stamp.

## Discrepancies

`WORK/discrepancy-log.json`:

```json
{
  "schema_version": 1,
  "discrepancies": [
    {"discrepancy_id": "DISC-004",
     "example_id": "WE-03-02",
     "official_source_id": "SRC-031",
     "official_result": "58.4 MPa",
     "our_result": "71.2 MPa",
     "reasoning": "The model answer omits the parallel-axis term for the flanges.",
     "confidence": "high",
     "resolution": "our_result_preferred"}
  ]
}
```

`resolution` is one of `our_result_preferred`, `official_preferred`,
`both_defensible`, `unresolved`. Every discrepancy referenced by a record must
appear here, and unresolved ones must be listed in the final report and in
`progress.unresolved_discrepancies`.
