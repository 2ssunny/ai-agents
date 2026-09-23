# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

**This skill reflects SDK capabilities through Phase 4, SDK docs commit `6a74d07`.**

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop`, 18 commits ahead of `origin/develop`. Local review only |
| Last reviewed commit | `6a74d07` — `docs: document Phase 4 geometry facts, queries and their verified limits` |
| Phase 1 | `3381f0c`, `e095234`, `b36c21f` |
| Phase 2 | `08b3dfc`, `e5a248a`, `ebb340a` |
| Phase 3 | `f2ee36f`, `b518ba3`, `a92fa7a` |
| Phase 4 | `335c797` geometry facts / semantic queries / safe plane edits, `60eb0ec` live validation, `6a74d07` docs |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-23 |
| Unit tests at review | 1156 passed, run during review in a standard CPython 3.14.2 venv (editable install of `develop`) |
| Live integration at review | 62 passed, 6 skipped, plus Phase 1–4 acceptance, per upstream docs. Phase 4 acceptance uses no raw COM, no topology indices and no descriptor parsing |
| CI | Last ran at `9b2f402`; the reviewed commits are unpushed |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline 6a74d07..HEAD
```

Upstream history was rewritten once when it was published (2026-09-16). If a
recorded commit is ever missing from the ancestry, compare trees with
`git diff <last-reviewed> HEAD` instead of reading `log <old>..HEAD`.

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | `SketchElement`, staleness and error categories promoted; export recorded as unavailable |
| `6ec5426` | Selection-restoring topology, one generation per Part, inspection of bodies / sets / topology counts |
| `1d7162f` | Environment-neutral skill (Conda optional) |
| `9b2f402` | `part.inspect.in_work_object()`; CI on Windows CPython 3.11–3.14 |
| `b36c21f` | **Phase 1**: body-scoped topology and ownership, targeted rebuilds, measurement and support preconditions, repair-before-delete |
| `a92fa7a` | **Phases 2–3**: feature editing, sketch rediscovery, `work_at`, parameter guard, circular pattern, booleans, constraint removal, suppression |
| `6a74d07` | **Phase 4**: measured geometry facts and semantic queries become the default way to select topology; owner semantics corrected; Pad/Pocket direction; editable and guarded reference planes; update diagnostics. New `geometry-query.md` |

## What changed for agents at this review

- **Geometry facts.** `face.geometry` (`surface_type`, `area_mm2`, `center_mm`,
  `perimeter_mm`, planar `normal` / `plane_origin_mm`, cylindrical `radius_mm`)
  and `edge.geometry` (`curve_type`, `length_mm`, points, line `direction`,
  circle/arc `radius_mm` / `center_mm` / `angle_deg`). Area is converted to mm²
  by the SDK.
- **Semantic queries.** `snapshot.query()` with type, orientation, size, position
  and current-owner steps; `one()` raises `TopologyQueryNoMatchError` or
  `TopologyQueryAmbiguousError`. Index- and descriptor-based selection is now
  deprecated in the skill.
- **Normal orientation limitation.** The planar normal is the supporting plane's
  orientation; top and bottom faces of a block reported the same sign. The skill
  teaches `normal_parallel(...).extreme(...)`.
- **Owner semantics.** `current_owner_feature_name` added; `owner_feature_name`
  documented as current ownership, not provenance. Owner-body resolution falls
  back to a unique name match and otherwise stays unknown.
- **Pad/Pocket direction.** `direction=` at creation, `direction`,
  `set_direction()`, `reverse_direction()`; `None` keeps CATIA's default, which
  for a Pocket can cut nothing while rebuilding successfully.
- **Editable reference planes.** `OffsetPlane.set_offset`, `AnglePlane.set_angle`.
- **In-use plane deletion guard.** `planes.dependents()`, `ReferenceInUseError`,
  `force=True`.
- **Update diagnostics.** `part.inspect.update_issues()` and
  `PartUpdateError.issues` — affected state, not root cause.
- **Rectangle limitation.** `rectangle()` creates four lines and no constraints.

## Deliberately not documented

- **A direction default change.** `direction=None` preserves CATIA's defaults;
  the skill does not claim otherwise.
- **Direction for Shaft, Groove and Rib**: not exposed.
- **Outward normals, adjacency, cone/sphere/spline facts, provenance**: not
  exposed, and listed as unsupported.
- **Exact performance figures.** Upstream observed roughly one second for a
  snapshot plus measurement on a small part and near-instant re-queries; the
  skill only teaches "reuse a measured snapshot within one generation".
- **Circular pattern on X or Y**, `Chamfer.Length2`, rectangular-pattern and
  multi-sections-solid dimensions, `Line2D` coordinates, dependency safety
  beyond formulas, suppression dependency prediction: unchanged from Phase 3.

## Observed upstream details

- `CircularPattern`, `BooleanOperation` and the `DIRECTION_*` constants live in
  `auto_3dx.geometry.part_design` and are not re-exported from
  `auto_3dx.geometry`. The skill imports the constants from `part_design`, as
  upstream's own contract does.
- `planes.get()` is annotated as returning the base `Plane`; the concrete object
  is an `OffsetPlane` or `AnglePlane`. The validator accepts members defined on
  an auto_3dx subclass for this reason.
- `ensure_pad` / `ensure_pocket` take no `direction`; only `create_*` and the
  setters do.

## Environment evidence

| Environment | Unit-tested | Live-tested |
|---|---|---|
| Standard CPython venv, editable install | 1156 passed (3.14.2, this review) | 62 passed, 6 skipped (3.14.2, pywin32 312) |
| Standard CPython venv, regular install | passed at an earlier commit | not run |
| Conda environment, editable install | passed at an earlier commit (3.11.16) | predates Phases 2–4 |
| GitHub Actions Windows runner | passed on 3.11–3.14 at `9b2f402` | none (no 3DEXPERIENCE) |

## Evidence reviewed

- `docs/api-design.md` section 19 (facts, queries, direction, planes,
  diagnostics, not-covered list) and section 7 (owner semantics, fallback)
- `docs/conventions.md` 1.13; `docs/capabilities.md`, `docs/status.md`,
  `README.md`
- `src/auto_3dx/`: `geometry/facts.py`, `geometry/query.py`, `geometry/edges.py`,
  `geometry/faces.py`, `geometry/planes.py`, `geometry/part_design.py`,
  `inspect/summary.py`, `errors.py`, `core/part.py`, plus introspection of the
  installed package for every signature used in the skill
- `tests/integration/test_phase4_live.py`, `scripts/acceptance/phase4_geometry.py`

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
   rules; `capabilities.md` for the matrix; `safety.md` for semantics;
   `geometry-query.md`, `topology.md`, `editing.md`, `part-design.md` for
   detail; `examples.md` for call shapes. Promote to Verified only with a live
   integration test. Never flatten partial support into "yes".
5. Add retired names to `RETIRED_NAMES` and new code-bearing reference files to
   `CODE_FILES` in `scripts/validate_skill.py`.
6. Run the validator with the interpreter whose auto-3dx installation should be
   checked: `python skills/global/auto-3dx/scripts/validate_skill.py`.
7. Search the skill for removed names, index or descriptor selection, outward-
   normal assumptions, provenance claims, stale recovery guidance, and
   machine-specific paths.
8. Update the tables above, including the phase marker at the top.
9. Review the diff. Commit only when the user asks; never push unasked.
