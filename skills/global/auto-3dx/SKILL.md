---
name: auto-3dx
description: Operating contract for driving a running 3DEXPERIENCE CATIA session through the auto-3dx Python SDK — attach, inspect an open Part, then create and edit parameters, formulas, sketches, planes, bodies, patterns, booleans and Part Design features, rebuild, and verify, without saving or bypassing the SDK's safety checks. Use when the user wants to read, modify, or build CAD geometry in 3DEXPERIENCE or CATIA from Python, mentions auto-3dx or auto_3dx, or asks for pads, pockets, fillets, holes, bolt circles, sketches, parameters, bodies or measurements on a live Part.
---

# auto-3dx — 3DEXPERIENCE CATIA automation

`auto-3dx` (import name `auto_3dx`) is the Python SDK that drives a running
3DEXPERIENCE CATIA session over Windows COM. This skill tells you how to use it
safely. It is not the API reference: signatures come from the installed package
(`help(...)`, docstrings) and, when available, its `docs/api-design.md`. **If
this skill and the installed package disagree, the package wins** — follow the
package and report the drift.

When the task is changing the SDK itself (inside the `auto-3dx` repository),
that repository's own contract and probe workflow govern instead of this skill.

## Preconditions

- Windows, 64-bit Python 3.11+, and a running 3DEXPERIENCE session with the
  target Part **already open and active**. The SDK attaches only: it cannot
  launch a session or create a Part or Product.
- **Python environment.** Use the interpreter the current project is configured
  with (its venv, Conda environment, or other documented convention) that has
  `auto_3dx` installed. Conda is one valid option, not a requirement: do not
  assume Conda, Anaconda, an environment name, or a machine-specific path, and
  do not create a new environment when one is configured. Confirm with
  `python -c "import auto_3dx; print(auto_3dx.__file__)"`, then `help()` on the
  class you need. If `auto_3dx` is not importable there, report that it is not
  installed and follow the project's conventions — do not silently switch
  interpreters.
- `com3dx` ships with the 3DEXPERIENCE installation; it is not a pip package and
  `Catia.attach()` finds it. Do not pip-install it, import it, or edit
  `sys.path` for it. Confirm you are pointed at the right document with
  `catia.active_window_title`, never a raw window read.

## Workflow

```text
inspect the model -> rediscover objects by name -> choose body/history context
  -> one logical mutation -> explicit update -> inspect/measure/verify -> repeat
```

1. **Attach and choose the Part.** `Catia.attach()`; `ActiveEditor` does not
   reliably follow the UI tab, so with several editors open use
   `catia.part_named(name)`. If the right Part is unclear, ask.
2. **Inspect before editing.** `part.inspect.summary()` reports the Part name,
   rebuild status, main-body features (`kind`, `supported`), sketch names, user
   parameters, every body, geometrical sets, edge and face counts, and the
   In-Work Object. If `up_to_date` is already `False`, report it before stacking
   changes.
3. **Rediscover, never remember.** The CATIA model is the source of truth. Find
   bodies, sketches, sketch elements, parameters, formulas, features, patterns
   and constraints by name each time; a Python handle from an earlier process is
   worthless (topology snapshots are process-local, see below).
4. **Choose the context.** `with part.work_in(body):` picks which body to model
   in; `with part.work_at(feature):` picks where in that body's history the next
   feature goes. Outside a block nothing touches the In-Work Object.
5. **Make one logical mutation** through the public API, then rebuild. Avoid
   large blind batches of geometry with no intermediate verification.
6. **Rebuild explicitly.** `part.update()` rebuilds the whole Part;
   `body.update()` or `part.update(body)` rebuilds one object without moving the
   In-Work Object. No `create_*`, `ensure_*`, `set_*`, `activate`/`deactivate` or
   `remove_*` call rebuilds on its own.
7. **Verify.** Check `part.is_up_to_date()` or `body.is_up_to_date`, re-read what
   you set, and compare `part.measurement.measure()` before and after. Measuring
   a target CATIA has not rebuilt raises `TargetNotUpToDateError`: rebuild first,
   because measurement never rebuilds for you.

For a risky edit, record the previous valid value first, then modify → update →
roll back and update again if it fails.

## Public API only

- From the package root import only `Catia`, `Part` and the error categories
  (`Auto3dxError`, `SessionError`, `ValidationError`, `NotFoundError`,
  `ConflictError`, `AutomationError`, `PartUpdateError`, `StaleSnapshotError`).
  Reach everything else through attributes (`part.sketches`, `part.bodies`,
  `part.part_design`, `part.topology`, ...); import specific errors from
  `auto_3dx.errors`.
- Never use `part.com_object`, `catia.com_object`, `win32com`, `com3dx`,
  `ShapeFactory`, `HybridShapeFactory`, `Selection`, or private `_…` members to
  do ordinary CAD work. `com_object` is the single escape hatch and is for
  read-only reads the SDK itself points to, such as a `SketchElement`'s radius.
- Raw Automation is appropriate **only** during explicit SDK-development or
  capability-probe work inside the auto-3dx repository.
- **If an ordinary modelling task reaches a missing public capability: stop and
  report the SDK gap.** Do not silently bypass it. Unsupported areas are listed
  in [references/capabilities.md](references/capabilities.md).

## Core safety rules

- **Topology is transient and body-owned.** Scope snapshots to the body you are
  building in, select edges by `owner_feature_name`, and take a fresh snapshot
  before every topology-consuming call — including after suppression. Details
  and limits: [references/topology.md](references/topology.md).
- **Update failure is repaired, not deleted.** See below.
- **Editing beats recreating.** Verified feature dimensions are editable in
  place; sketch elements are rediscovered by name; a parameter a formula reads is
  protected from removal. Details:
  [references/editing.md](references/editing.md).
- **Some operations consume or invalidate other objects.** A boolean consumes its
  tool body permanently; suppression can break downstream features. Details:
  [references/part-design.md](references/part-design.md).
- Selection-based operations (topology search, `remove_*`, body visibility,
  constraint removal) need the **active** Part, or `InactivePartError`.
- A plane from `part.planes` cannot support a sketch until it has been rebuilt:
  `SupportNotUpdatedError` means `part.update()`, then create the sketch — not a
  blind retry.
- Reading an `EnumParam` works, so parameter listing is not broken by one.
  Writing one is not supported.

## Update failure and recovery

`PartUpdateError` means the model is invalid and every later rebuild fails until
it is repaired. **Repair first; deletion is the last resort.** Nothing is rolled
back or deleted automatically.

1. Stop mutating and identify what the failure followed.
2. **A reversible edit to a previously valid model** — a dimension, parameter,
   formula value, or a suppression you just applied: restore the previous value
   or state and rebuild again. CATIA heals the model and dependent features
   survive.
3. Confirm with `part.is_up_to_date()`, or `body.is_up_to_date` for one body.
4. **A newly created feature that never rebuilt**, or an edit whose previous
   value is unknown, or a rollback that itself failed: remove the offending
   feature with its `remove_*` method, then rebuild.
5. Report what failed and what you did. Not every update failure is recoverable;
   do not promise otherwise, and never delete downstream features to force one
   through.

## Multi-body work

```python
body = part.bodies.create("ToolBody")
with part.work_in(body):
    sketch = part.sketches.create("TOOL_PROFILE", support="XY")
    part.part_design.create_pad("TOOL_PAD", sketch, 20.0)
body.update()
edges = part.topology.edges(body=body)
properties = part.measurement.measure(body)
```

`part.bodies` offers `list`, `names`, `get`, `main`, `create`,
`remove(name, delete_contents=False)`, plus per-body `hide()` / `show()` /
`is_visible`. Bodies are re-found in the model. Leaving a `work_in` block
rebuilds nothing, so update the body before measuring it. The main body is never
removed, and removing a body with content needs `delete_contents=True`, which
deletes everything inside it.

## Persistence and destructive actions

- The SDK never calls `Save()` or `PLMPropagate()` and has no export API. Edits
  live in the session until the user saves in the UI, where a save commits to the
  server with every other unsaved change. Never save, propagate or export on the
  user's behalf; when work is done, say it is unsaved.
- Deleting geometry, parameters, formulas, constraints or bodies you did not
  create in this task requires explicit user intent naming the object. Remember
  the cascades: removing a Pad removes its sketch, `delete_contents=True` empties
  a body, and `remove_boolean(..., delete_consumed_body=True)` destroys the
  consumed tool body for good.

## References

| File | Contents |
|---|---|
| [capabilities.md](references/capabilities.md) | What is supported, partially supported, and not |
| [safety.md](references/safety.md) | Errors, generation, removal side effects, raw-COM policy |
| [topology.md](references/topology.md) | Body-scoped topology, ownership, staleness |
| [editing.md](references/editing.md) | Feature dimensions, sketch rediscovery, `work_at`, parameter dependencies |
| [part-design.md](references/part-design.md) | Circular pattern, booleans, constraint removal, suppression |
| [examples.md](references/examples.md) | Minimal end-to-end patterns |
| [upstream-sync.md](references/upstream-sync.md) | Maintenance: last reviewed SDK state |
