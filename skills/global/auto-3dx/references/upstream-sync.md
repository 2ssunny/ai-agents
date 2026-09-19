# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

**This skill reflects SDK capabilities through Phase 3, SDK commit `a92fa7a`.**

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop`, 15 commits ahead of `origin/develop`. Local review only |
| Last reviewed commit | `a92fa7a` — `docs: document Phase 3 operations and their verified limits` |
| Phase 1 | `3381f0c` safety fixes, `e095234` live validation, `b36c21f` docs |
| Phase 2 | `08b3dfc` existing-model editing, `e5a248a` live validation, `ebb340a` docs |
| Phase 3 | `f2ee36f` patterns / booleans / constraint removal / suppression, `b518ba3` live validation and raw-COM removal, `a92fa7a` docs |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-19 |
| Unit tests at review | 1089 passed, run during review in a standard CPython 3.14.2 venv (editable install of `develop`) |
| Live integration at review | 56 passed, 6 skipped, plus Phase 1, Phase 2 and Phase 3 acceptance scripts, per upstream docs. Acceptance uses the public API only |
| CI | Last ran at `9b2f402`; the reviewed commits are unpushed, so no CI result covers them |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline a92fa7a..HEAD
```

Upstream history was rewritten once when it was published (2026-09-16). If a
recorded commit is ever missing from the ancestry, compare trees with
`git diff <last-reviewed> HEAD` instead of reading `log <old>..HEAD`.

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | Live rerun promoted `SketchElement`, staleness and the error categories to Verified; export recorded as unavailable |
| `6ec5426` | Selection-restoring topology searches, one generation per CATIA Part, `part.inspect` bodies / sets / topology counts |
| `1d7162f` | Packaging and docs; the skill became environment-neutral (Conda is optional) |
| `9b2f402` | `part.inspect.in_work_object()`; CI on Windows CPython 3.11–3.14 |
| `b36c21f` | **Phase 1**: body-scoped topology with ownership and `CrossBodyReferenceError`, `body.update()` / `part.update(target)`, `TargetNotUpToDateError`, `SupportNotUpdatedError`, `InactivePartError`, `EnumParam` reads. Update-failure guidance reversed to repair-before-delete |
| `a92fa7a` | **Phases 2–3**: feature dimension editing, sketch element rediscovery, `work_at(feature)`, parameter dependency guard, circular pattern, multi-body booleans, constraint removal, feature suppression, `catia.active_window_title`. Skill reorganised into `topology.md`, `editing.md` and `part-design.md` |

## What changed for agents at this review

**Phase 2 — editing an existing model.**

- Verified feature dimension setters: fillet `radius`; chamfer `length1` and
  `angle`; hole `diameter` and `depth`; shell `internal_thickness` and
  `external_thickness`; thickness `offset`. Setters do not rebuild.
- `sketch.elements()`, `sketch.get_element(name)`, `SketchElement.name` / `kind`
  / `radius`, and `SketchElementNotFoundError`.
- `part.work_at(feature)` for the history insertion position, distinct from
  `work_in(body)`.
- `part.parameters.dependents(name)` and the `ParameterInUseError` guard, driven
  by `Formula.GetInParameter` rather than by parsing formula text.

**Phase 3 — core CAD operations.**

- `create_circular_pattern(name, feature, angular_instances,
  angular_spacing_deg, axis="Z")` with list/get/remove and an editable angular
  row; `radial_instances` read-only.
- `create_boolean_remove` / `_add` / `_intersect` / `_assemble`, with the tool
  body consumed permanently and `remove_boolean(..., delete_consumed_body=True)`
  as the destructive removal.
- `sketch.constraints.remove(...)`, edit-state aware.
- `is_active` / `activate()` / `deactivate()` on Part Design features, advancing
  the model generation.
- `catia.active_window_title`, so scripts need no raw window read.

## Deliberately not documented

- **Circular pattern on X or Y.** Only `"Z"` was verified; the other origin
  planes rotated about something the test geometry could not identify.
- **`Chamfer.Length2`**, a generic `Hole.Depth`, generic `Thickness.Thickness` /
  `.Value`, rectangular-pattern dimensions, multi-sections-solid dimensions:
  each verified absent or unwritable, not merely untried.
- **`Line2D` coordinate reads**: no coordinate members in this release.
- **Dependency safety beyond formulas**: rules, checks, laws, programs and
  design tables expose no verified input list.
- **Suppression dependency analysis**: the SDK does not predict which
  suppressions are safe, so the skill teaches suppress → update → reactivate.
- **Per-instance pattern activation, boolean operand replacement, consumed-body
  restoration**: no public API.

## Observed upstream detail

`CircularPattern` and `BooleanOperation` are reachable through
`auto_3dx.geometry.part_design` but are not re-exported from
`auto_3dx.geometry`, unlike the other feature wrappers. Nothing in the skill
depends on importing them directly — agents reach them through
`part.part_design` — but it is worth raising upstream on the next pass.

## Environment evidence

| Environment | Unit-tested | Live-tested |
|---|---|---|
| Standard CPython venv, editable install | 1089 passed (3.14.2, this review) | 56 passed, 6 skipped (3.14.2, pywin32 312) |
| Standard CPython venv, regular install | passed at an earlier commit | not run |
| Conda environment, editable install | passed at an earlier commit (3.11.16) | predates Phases 2–3 |
| GitHub Actions Windows runner | passed on 3.11–3.14 at `9b2f402` | none (no 3DEXPERIENCE) |

Remaining limitations: live integration has run on CPython 3.14.2 only for
Phases 2–3; 32-bit Python, Microsoft Store Python and 3DEXPERIENCE releases
other than `B428_Cloud` are unverified.

## Evidence reviewed

- `docs/api-design.md` sections 15, 17 and 18, plus the migration table
- `docs/conventions.md` 1.10 (body topology), 1.11 (editing matrix, including
  every dimension that failed), 1.12 (patterns, booleans, constraints,
  suppression)
- `docs/capabilities.md`, `docs/status.md`
- `src/auto_3dx/`: `errors.py`, `core/part.py`, `core/application.py`,
  `geometry/part_design.py`, `geometry/sketch.py`, `geometry/constraint.py`,
  `geometry/bodies.py`, `geometry/topology.py`, `parameters/collection.py`,
  `formulas/`, plus introspection of the installed package for exact signatures
- `tests/integration/test_editing_live.py`, `test_phase3_live.py`, and the
  `scripts/acceptance/phase2_editing.py` / `phase3_operations.py` scripts

## Sync procedure

1. `git status` and `git log <last-reviewed>..HEAD` in the auto-3dx clone; if the
   commit is not an ancestor, compare trees instead. Read the diffs touching
   `src/`, `docs/api-design.md`, `docs/conventions.md`, `docs/capabilities.md`,
   `docs/status.md`, `README.md`, `tests/integration/` and `scripts/`.
2. Ignore internal refactors that leave the public API, safety semantics and
   evidence state unchanged.
3. Verify exact names by introspecting the installed package, not from any
   prompt or summary.
4. Update the smallest part of the skill: `SKILL.md` for workflow and core
   rules, `references/capabilities.md` for the matrix, `references/safety.md`
   for semantics, `references/topology.md`, `references/editing.md`,
   `references/part-design.md` for detail, `references/examples.md` for call
   shapes. Promote to Verified only with a live integration test; a CI run is
   unit evidence only. Never flatten partial support into "yes".
5. Add newly retired names to `RETIRED_NAMES` in `scripts/validate_skill.py`,
   and list new code-bearing reference files in `CODE_FILES`.
6. Run the validator with the interpreter whose auto-3dx installation should be
   checked: `python skills/global/auto-3dx/scripts/validate_skill.py`.
7. Search the skill for removed or renamed names, stale recovery guidance, and
   machine-specific interpreter paths.
8. Update the tables above, including the phase marker at the top.
9. Review the diff. Commit only when the user asks; never push unasked.
