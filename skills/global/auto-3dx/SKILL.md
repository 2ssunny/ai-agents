---
name: auto-3dx
description: Operating contract for driving a running 3DEXPERIENCE CATIA session through the auto-3dx Python SDK — attach, inspect an open Part, then change parameters, formulas, sketches, planes and Part Design features, rebuild, and verify, without saving or bypassing the SDK's safety checks. Use when the user wants to read, modify, or build CAD geometry in 3DEXPERIENCE or CATIA from Python, mentions auto-3dx or auto_3dx, or asks for pads, pockets, fillets, sketches, parameters, or measurements on a live Part.
---

# auto-3dx — 3DEXPERIENCE CATIA automation

`auto-3dx` (import name `auto_3dx`) is the Python SDK that drives a running
3DEXPERIENCE CATIA session over Windows COM. This skill tells you how to use it
safely. It is not the API reference: signatures and details come from the
installed package (`help(...)`, docstrings) and, when the repository is
available, its `docs/api-design.md`. **If this skill and the installed package
disagree, the package wins** — follow the package and report the drift.

When the task is changing the SDK itself (inside the `auto-3dx` repository),
that repository's own contract and probe workflow govern instead of this skill.

## Preconditions

- Windows, 64-bit Python 3.11+, and a running 3DEXPERIENCE session with the
  target Part **already open**. The SDK attaches only: it cannot launch a
  session or create a Part or Product.
- **Python environment.** Use the interpreter the current project is configured
  with (its venv, Conda environment, or other documented convention) that has
  `auto_3dx` installed. Conda is one valid option, not a requirement: do not
  assume Conda, Anaconda, an environment name, or a machine-specific
  interpreter path, and do not create a new environment when one is configured.
- Confirm what that interpreter has installed before relying on it:
  `python -c "import auto_3dx; print(auto_3dx.__file__)"`, then `help()` on the
  class you need. Never write calls from memory of an older version.
- If `auto_3dx` is not importable there, report that auto-3dx is not installed
  in that environment and follow the project's setup conventions. Do not
  silently switch to some other interpreter you happen to find.
- `com3dx` ships with the 3DEXPERIENCE installation; it is not a pip package.
  `Catia.attach()` finds it (explicit path, `AUTO_3DX_COM3DX_PATH`, or the
  registered `CATIA.Application` server). Do not pip-install it, import it, or
  edit `sys.path` for it. On `Com3dxNotFoundError`, report it: choosing a
  specific release path is the user's decision.
- Verified Python environments and current capability state:
  [references/capabilities.md](references/capabilities.md).

## Workflow

```text
attach -> choose the Part explicitly -> inspect -> resolve targets
  -> plan the smallest change -> mutate via public API -> part.update()
  -> verify the observable result -> inspect again when anything is unclear
```

1. **Attach.** `Catia.attach()`. `ActiveEditor` does not reliably follow the
   UI tab, so when more than one editor is open (`catia.editors()`), select
   with `catia.part_named(name)`. If the right Part is unclear, ask.
2. **Inspect before editing.** `part.inspect.summary()` returns the Part name,
   rebuild status, main-body features (with `kind` and whether the SDK
   `supported` it), sketch names, user parameters, every body, the geometrical
   sets directly under the Part with their elements, and edge and face counts.
   Use `get`/`list`/`names` on collections for more. It does not report the
   contents of nested geometrical sets, sets inside a body, or sketches inside a
   set — do not claim facts about them. If `up_to_date` is already `False`,
   report it before stacking changes.
3. **Resolve targets by name.** `NotFoundError` or `AmbiguousNameError` means
   ask the user; never pick the first match. Do not overwrite or reuse an
   existing user object unless the request clearly refers to it. Give objects
   you create distinct names.
4. **Plan the minimum change.** Group mutations that are only valid together
   (a sketch and the pad built on it) before a single rebuild.
5. **Mutate through the public API** (next section).
6. **Rebuild explicitly.** `part.update()` is the only call that rebuilds. No
   `create_*`, `ensure_*`, `set*` or `remove_*` call rebuilds on its own.
7. **Verify.** A successful update does not prove the intended geometry. Check
   `part.is_up_to_date()`, re-read the values you set, compare
   `part.measurement.measure()` (volume, area, mass, centre of gravity) before
   and after, and report the numbers.

Minimal usage patterns: [references/examples.md](references/examples.md).

## Public API only

- From the package root import only `Catia`, `Part` and the error categories
  (`Auto3dxError`, `SessionError`, `ValidationError`, `NotFoundError`,
  `ConflictError`, `AutomationError`, `PartUpdateError`, `StaleSnapshotError`).
  Reach everything else through attributes (`part.sketches`,
  `part.part_design`, `part.topology`, ...); import specific errors and
  warnings from `auto_3dx.errors`.
- Do not use `win32com`, `com3dx`, `pywintypes`, `CATIA.Application`,
  `ShapeFactory`, `HybridShapeFactory`, `Selection` or other Automation calls
  directly for CAD work.
- `com_object` is the SDK's single escape hatch (there is no `raw`). It skips
  validation, generation tracking and every safety rule. In ordinary work use
  it only for **read-only** property reads the SDK itself points to (for
  example a `SketchElement`'s radius). Raw mutations belong only to explicit
  SDK development or probing that the user asked for.
- **A missing capability is a finding, not a puzzle.** Tell the user the
  operation is not exposed by the installed auto-3dx, and offer the options: a
  manual step in the CATIA UI, or SDK work in the auto-3dx repository. Do not
  invent a raw-COM workaround in the user's project unless they explicitly ask.

## Topology references are transient

- `part.topology.edges()` / `part.topology.faces()` return a snapshot of the
  **whole solid**. `Edge.index` / `Face.index` is a position in that snapshot,
  not an identity; `descriptor` is for logging only and cannot be resolved later.
- Any mutation through any wrapper of the same CATIA Part — creating, removing
  or renaming anything, writing any parameter or dimension value, closing a
  `sketch.edit()` block, and `part.update()` whether it succeeds or fails —
  makes every earlier snapshot stale. The generation is shared by the
  underlying Part, whichever `active_part()`, `part_named()` or `parts()` call
  produced the wrapper. Using a stale snapshot raises `StaleSnapshotError`
  before CATIA is touched.
- Take a fresh snapshot immediately before each topology-consuming call. After
  `StaleSnapshotError`, re-snapshot **and re-identify the target**: the same
  index in a new snapshot can be a different edge. Never retry with the old
  handle or pass its `com_object` to get past the check.
- Changes made in the CATIA UI or by another script are invisible to the
  staleness check, which is another reason to snapshot right before use.
- No verified selector finds "the top face" or "the edge at X". When the user
  needs a specific edge or face and the SDK cannot prove which one it is, say
  so and ask; do not guess from an index.
- Taking a snapshot (and `part.inspect.summary()`, which counts topology)
  restores the user's CATIA selection. If CATIA silently refuses part of the
  restore, the snapshot is still returned with `SelectionNotRestoredWarning`:
  the snapshot is valid and the model is unchanged; only the UI selection was
  lost. Keep the snapshot, do not retry or repair the selection with raw COM,
  and tell the user they may need to re-select. The warning is not an
  `Auto3dxError`, so never silence it with a blanket filter.

## Ownership and context checks

A `SketchEditor` is valid only inside its own `with sketch.edit()` block;
constraints can only be created there; `edit()` is not re-entrant; a
`SketchElement` drawn in one sketch is refused by another sketch. Assembly
contexts raise `NoActivePartError`. Every `ValidationError` guarantees the model
was not touched: fix the call, never unwrap to raw COM to force it through.

## Update failure and error handling

- After `PartUpdateError`, the offending feature is **still in the model and
  every later update fails until it is removed**. Stop mutating, remove it with
  the matching `remove_*` method (a rectangular pattern is removed by passing
  its wrapper), call `part.update()` again to confirm recovery, and report. The
  SDK does not roll back; do not retry blindly.
- `AutomationError` means CATIA was called and the model may have changed:
  inspect before continuing. `PartialCreationError` means an object was left
  behind under a default name: find it and clean it up before retrying.
- Error categories, removal side effects and naming traps:
  [references/safety.md](references/safety.md).

## Persistence and destructive actions

- The SDK never calls `Save()` or `PLMPropagate()` and has no export API. Edits
  live in the session until the user saves in the UI. In 3DEXPERIENCE a save
  commits to the server and includes every unsaved change in the session.
- Never save, propagate, or export on the user's behalf, and never reach for raw
  COM to do so. When the work is done, tell the user it is unsaved.
- Deleting geometry, parameters or formulas you did not create in this task
  requires explicit user intent naming the object. Clean up only what you
  created, and remember the cascades (removing a Pad also removes its sketch).

## Maintenance

This skill tracks the upstream SDK. The last reviewed upstream state and the
sync procedure are in [references/upstream-sync.md](references/upstream-sync.md);
agents using the skill do not need that file.
