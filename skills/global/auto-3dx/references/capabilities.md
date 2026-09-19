# auto-3dx capability state

What an agent may rely on today, through SDK Phase 3. Detailed signatures live
in the installed package (`help(auto_3dx.geometry.part_design.PartDesign)` and
similar), not here. When the installed package disagrees with this page, trust
the package and report the drift.

Upstream state reviewed: see `upstream-sync.md`. Live evidence comes from one
installation (`B428_Cloud`); other 3DEXPERIENCE releases are unverified.

## How to read the labels

| Label | Meaning |
|---|---|
| **Verified** | Backed by a live probe and a live integration test: the call succeeded, the rebuild succeeded, and the result was checked. |
| **Partial** | Supported within stated limits only. The limits are part of the capability — do not round them up to "yes". |
| **Not supported** | Absent from the public API. Do not assume it, and do not recreate it with raw COM in a user's project. |

## Python environment

auto-3dx is an ordinary Windows package installed with pip. Its only runtime
dependency is `pywin32`; `com3dx` comes from the 3DEXPERIENCE installation and is
found at runtime. No Python distribution is privileged. Upstream evidence, all
64-bit, live runs on `B428_Cloud`:

| Environment | Python | pywin32 | Unit suite | Live integration |
|---|---|---|---|---|
| Standard CPython venv (python.org), editable install | 3.14.2 | 312 | 1089 passed | **Verified**: 56 passed, 6 skipped |
| Standard CPython venv, regular install | 3.14.2 | 312 | passed at an earlier commit | not run |
| Conda environment (Anaconda), editable install | 3.11.16 | 312 | passed at an earlier commit | 38 passed, 1 skipped, at an earlier commit |
| GitHub Actions Windows runner, regular install | 3.11, 3.12, 3.13, 3.14 | pip-resolved | passed at an earlier commit | none (no 3DEXPERIENCE on the runner) |

- The 6 skips need a Part prepared by hand; they are not failures.
- Phase 1, Phase 2 and Phase 3 acceptance scripts all pass, and they use the
  public API only.
- Live runs use a disposable Part named by `AUTO3DX_LIVE_PART`.
- Pending: live integration on Python 3.12 and 3.13 (unit only), the Phase 2–3
  work on Conda, 32-bit Python, Microsoft Store Python, and 3DEXPERIENCE
  releases other than `B428_Cloud`.

## Capability matrix

| Area | Status | Notes |
|---|---|---|
| Session / attach | Verified | `Catia.attach()`, `active_part()`, `editors()`, `parts()`, `part_named()`, `active_window_title`. Assembly context refused (`NoActivePartError`) |
| Active-Part guard | Verified | Selection-based work (topology search, `remove_*`, visibility, constraint removal) refuses a non-active Part with `InactivePartError` |
| Parameters | Verified | list/get/set/remove, typed `create_*`/`ensure_*`, unit catalogue. `EnumParam` **read** only — writing is not supported |
| Parameter dependency safety | Partial | `dependents(name)` and the removal guard (`ParameterInUseError`) cover **formula** inputs, read from the model. Rules, checks, laws, programs and design tables are not covered; `force=True` overrides |
| Formula | Verified | create/ensure/get/list/remove, `relation_name()`, modify/rename/activate/deactivate, `reading(parameter)`, `Formula.inputs()`, `Formula.reads(parameter)` |
| Sketch | Verified | create on origin planes or a user plane, ensure (origin strings only), get/list/names/remove/rename, `support()`, `set_center_line()` |
| Sketch geometry | Verified | inside `edit()`: point, line, circle, arc, spline, rectangle, `set_construction` |
| SketchElement rediscovery | Partial | `sketch.elements()`, `sketch.get_element(name)` (`SketchElementNotFoundError`), `name`, `kind`, and `radius` for circles. **Line coordinates are not exposed** in this release |
| Constraints | Verified | 10 constraint kinds, inside `edit()` only; list/names/get, `broken_count`, dimensional read/write |
| Constraint deletion | Verified | `sketch.constraints.remove(constraint_or_name)`, edit-state aware, verified after fresh-process rediscovery |
| Planes | Verified | `create_offset`, `create_angle`, list/names/get, `remove(plane)`, `remove_geometrical_set()`. A new plane needs a rebuild before it can support a sketch (`SupportNotUpdatedError`) |
| Bodies | Verified | list/names/get/main/create/`remove(name, delete_contents=False)`, `is_up_to_date`, `update()`, `hide()`/`show()`/`is_visible`. Model-backed rediscovery |
| `work_in(body)` | Verified | Targets sketches, features and topology at one body; restores the previous In-Work Object on every exit; nests |
| `work_at(feature)` | Verified | Sets the history insertion position; CATIA inserts immediately after the chosen feature, moving nothing. Restores the previous In-Work Object on every exit |
| Pad, Pocket | Verified | create/ensure/get/list/remove; depth (`Pad.height`) read and write |
| Shaft, Groove | Verified | Need a centre line; first/second angle read and write |
| Rib, Slot | Verified | Profile plus path sketches |
| Mirror | Verified | Origin plane |
| Rectangular Pattern | Partial | `create_rectangular_pattern` along signed axes and `remove_rectangular_pattern(pattern)`. **Dimensional editing is not supported** |
| Circular Pattern | Partial | `create_circular_pattern(name, feature, angular_instances, angular_spacing_deg, axis="Z")`, list/get/remove, editable `angular_instances` and `angular_spacing_deg`. **Z axis only**; `radial_instances` read-only; no per-instance activation |
| Fillet | Verified | `create_edge_fillet` on a body-scoped `Edge`; `radius` / `set_radius` / `radius_parameter()` |
| Chamfer | Partial | `create_chamfer`; `length1` / `set_length1` and `angle` / `set_angle`. **Length2 cannot be written** in the mode this SDK creates |
| Shell | Verified | `create_shell` on a `Face`; `internal_thickness` and `external_thickness` with setters |
| Thickness | Verified | `create_thickness` on a `Face`; `offset` / `set_offset` |
| Hole | Partial | `create_hole` on a `Face`; `diameter` and `depth` with setters. No thread, countersink, counterbore or hole-family configuration |
| MultiSectionSolid | Partial | create/get/remove, **sections only**. No guides, no closing-point or coupling control, no dimensional editing |
| Boolean Remove / Add / Intersect / Assemble | Verified | `create_boolean_*(name, tool_body)` with the work body as target; `boolean_operations`, `get_boolean`, `operation`, `tool_body_name`. **The tool body is consumed permanently** |
| Boolean removal | Verified, destructive | `remove_boolean(name, delete_consumed_body=True)` destroys the consumed body; it does not come back |
| Feature suppression | Verified | `is_active`, `activate()`, `deactivate()` on Part Design feature wrappers (live-tested on Pad, Pocket, Fillet). Advances the generation; no dependency analysis |
| Topology | Partial | Part-wide or `body=`-scoped snapshots with `owner_body`, `owner_body_name`, `owner_feature_name`, and the `CrossBodyReferenceError` guard. **No feature-level scoping**, no persistent identity, registry is process-local |
| Measurement | Verified | `measure(item)` → `volume_mm3`, `area_mm2`, `mass_kg`, `cog_mm`; a `Body` may be passed. Refuses a target that is not rebuilt (`TargetNotUpToDateError`) and never rebuilds |
| Inspection | Verified | `part.inspect.summary()` and its parts, including bodies, geometrical sets, topology counts and the In-Work Object. Changes nothing |
| Deletion | Verified | Per-kind `remove_*`; cascades documented in `safety.md` §4 |
| Rebuild | Verified | `part.update()`, `part.update(target)`, `body.update()`, `part.is_up_to_date(target=None)`, `body.is_up_to_date` |

## Not supported

If a task needs one of these, **stop and report the SDK gap**. Do not reach for
raw COM.

- Circular Pattern on the X or Y axis; per-instance activation; advanced radial
  control.
- Rectangular Pattern dimensional editing.
- Restoring a consumed Boolean tool body; replacing a Boolean operand.
- Advanced Hole families and configuration; full thread, countersink and
  counterbore editing.
- General suppression dependency analysis (which suppressions are safe).
- Loft guides, closing points and coupling; broad GSD surface geometry; Split.
- Feature-level topology scoping; persistent cross-process topology identity.
- A complete Formula / Rule / Check / Law dependency graph.
- Writing an `EnumParam`; line-coordinate reads on `Line2D`.
- Setting the In-Work Object outside `work_in` / `work_at`.
- Renaming or reordering bodies; geometrical sets inside a body; axis systems.
- Inspection of nested geometrical set contents or sketches inside a set.
- Product / Assembly editing; PLM object creation.
- `Save`, `SaveAs`, `PLMPropagate`, and export (`ExportData` fails with `E_FAIL`
  on PLM-backed documents).
- Use from worker threads (main thread only).

## Known limitations of the safety guards

- The cross-body guard allows an operation through when CATIA reports no owner.
- A body-scoped snapshot can include sketch wire edges, which a fillet or chamfer
  cannot consume; filter with `owner_feature_name`.
- The generation registry is process-local: a new process must take fresh
  topology snapshots.
- Suppression safety is not predicted; suppressing an upstream feature can make
  the next rebuild fail.

## Deprecated — do not use in new code

| Deprecated | Use instead |
|---|---|
| `part.part_design.snapshot_edges()` / `snapshot_faces()` | `part.topology.edges()` / `faces()` |
| `SolidMeasurement.editor_com_object` | `com_object` |
| Passing raw 2D COM objects to constraints or `set_center_line` | Pass the `SketchElement` the editor returned or `sketch.get_element(name)` |
| `catia.com_object.ActiveWindow.Caption` | `catia.active_window_title` |
| Deleting and recreating a feature to change a verified dimension | The feature's own setter (`editing.md`) |
