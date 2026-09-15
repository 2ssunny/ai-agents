# auto-3dx capability state

What an agent may rely on today. Detailed signatures live in the installed
package (`help(auto_3dx.geometry.part_design.PartDesign)` and similar), not
here. When the installed package disagrees with this page, trust the package
and report the drift.

Upstream state reviewed: see `upstream-sync.md`. Live evidence comes from one
installation (`B428_Cloud`); other 3DEXPERIENCE releases are unverified.

## How to read the labels

| Label | Meaning |
|---|---|
| **Verified** | Backed by a live probe and a live integration test: the call succeeded, `Part.Update()` succeeded afterwards, and the result was checked. |
| **Implemented, not yet re-run live** | In the public API and unit-tested, built on reads or calls that were live-verified earlier, but this exact public path has not been through a live session since it was added or refactored. Use it, and report anything surprising. |
| **Not supported** | Absent from the public API. Do not assume it, and do not recreate it with raw COM in a user's project. |

## Verified

| Area | What works |
|---|---|
| Session | `Catia.attach()` to a running session (explicit `com3dx.py` path, `AUTO_3DX_COM3DX_PATH`, or registry discovery); `active_part()`, `editors()`, `parts()`, `part_named()`; an Assembly context is refused with `NoActivePartError` |
| Parameters | `list`, `names`, `user_parameters`, `user_names`, `get`, `set`, `remove`; `create_*` / `ensure_*` for length, real, integer, string, boolean, and `dimension` with a named magnitude; `parameters.units` catalogue. Units are checked, never converted |
| Formulas | `part.formulas`: `list`, `names`, `get`, `create`, `ensure`, `remove`, `relation_name()`; `Formula.modify`, `rename`, `activate`, `deactivate` |
| Sketches | `create` on `"XY"`/`"YZ"`/`"ZX"` or on a plane from `part.planes`; `ensure` (origin-plane strings only); `get`, `list`, `names`, `remove`, `rename`, `support()`, `set_center_line()` |
| Sketch geometry | inside `with sketch.edit() as editor`: `point`, `line`, `circle`, `arc`, `spline`, `rectangle`, `set_construction`. `arc` start/end parameters are passed through with an unverified unit |
| Sketch constraints | inside `edit()` only: `horizontal`, `vertical`, `perpendicular`, `parallel`, `coincident`, `tangent`, `concentric`, `length`, `radius`, `distance`; `sketch.constraints` lists them, reports `broken_count`, reads and writes dimensional values |
| Planes | `part.planes.create_offset`, `create_angle`; `remove(plane)`; `remove_geometrical_set()` |
| Sketch-based features | Pad, Pocket (create / ensure / get / list / remove, read and set depth); Shaft, Groove (need a centre line; read and set angles); Rib, Slot (profile and path sketches); Mirror (origin plane) |
| Pattern | `create_rectangular_pattern` of a `Pad` along signed axes; cleanup with `remove_rectangular_pattern(pattern)` |
| Edge features | `create_edge_fillet`, `create_chamfer` on an `Edge` from `part.topology.edges()`; get / list / remove by name |
| Face features | `create_shell`, `create_thickness`, `create_hole` on a `Face` from `part.topology.faces()`; get / list / remove by name |
| Rebuild | `part.update()`; `part.is_up_to_date(target=None)` reports rebuild status, not unsaved changes |
| Measurement | `part.measurement.measure()` returns `volume_mm3`, `area_mm2`, `mass_kg`, `cog_mm` |

## Implemented, not yet re-run live

The last live integration run predates the upstream refactor that introduced
these. Their behaviour is pinned by unit tests.

- `part.inspect.summary()` / `features()` / `sketches()` / `parameters()`:
  Part name, rebuild status, main-body features with `kind` and `supported`,
  sketch names, user parameters.
- `SketchEditor` geometry returning `SketchElement` (`kind`, `com_object`), and
  the refusal of an element drawn in a different sketch.
- One shared model generation across every collection of a `Part`, so any
  mutation through the Part makes topology snapshots stale.
- `part.measurement.measure()` with no argument measuring the main body.
- Error categories (`SessionError`, `ValidationError`, `NotFoundError`,
  `ConflictError`, `AutomationError`) and the small package root.

## Not supported

- Launching a session; creating a Part, Product, or any PLM object.
- `Save`, `SaveAs`, `PLMPropagate`, and any file export (STEP, STL, ...).
- Assembly editing: products, occurrences, assembly constraints.
- Relations other than formulas (laws, design tables, checks, rules).
- Deleting sketch constraints; diameter constraints.
- Bodies other than the main body; geometrical sets (beyond the one the SDK
  creates for its own planes); axis systems; surface (GSD) geometry.
- Inspection of other bodies, geometrical sets, or edge and face counts.
- Persistent or semantic edge/face identity, feature-scoped topology search, or
  selecting an edge or face by geometry.
- Bounding boxes or extents (removed because CATIA silently returned zeros).
- Unit conversion of parameter values.
- Part Design features beyond the thirteen above (Draft, Stiffener, circular
  and user patterns, loft, split, trim, boolean combine, ...).
- `ensure` for planes, edge and face features, and patterns; looking a pattern
  up by name; `sketches.ensure` on a user-defined plane.
- Use from worker threads (main thread only).

## Deprecated — do not use in new code

| Deprecated | Use instead |
|---|---|
| `part.part_design.snapshot_edges()` / `snapshot_faces()` | `part.topology.edges()` / `faces()` |
| `SolidMeasurement.editor_com_object` | `com_object` |
| Passing raw 2D COM objects to constraints or `set_center_line` | Pass the `SketchElement` the editor returned; a raw object skips the owner check |
