# auto-3dx safety semantics

Detail behind the rules in `SKILL.md`. Upstream source of truth:
`docs/api-design.md` (sections 5–9, 12, 15–18).

## 1. Model generation

Each CATIA Part has one generation counter, shared by every `Part` wrapper of
that Part (matched by COM identity) and by every collection and wrapper reached
through them. Topology snapshots are stamped with it and refused once it moves.

| Operation through the SDK | Advances |
|---|---|
| Creating any feature, sketch, plane, parameter, formula or body | yes |
| Removing any of them, including a constraint or a boolean | yes |
| Writing a value: parameter `set`, any feature `set_*` dimension, constraint `set_value` | yes |
| Activating or deactivating a feature | yes |
| Hiding or showing a body | yes |
| Closing a `sketch.edit()` block (once per block) | yes |
| `part.update()` / `body.update()`, success **or** failure | yes |
| A call that raised after reaching CATIA | yes — it advances on attempt |
| A `ValidationError` raised before any COM call | no |
| Reads: `list`, `get`, `names`, measurement, inspection, taking a snapshot | no |

Consequences:

- A parameter write stales snapshots even when the parameter drives nothing.
- Changes made in the CATIA UI or by another script do not advance it.
- A rebuild through one wrapper stales snapshots taken through another wrapper of
  the same Part. Re-reading the Part is safe.
- **The registry is process-local.** A new Python process starts with its own
  counter, so an index or assumption carried over means nothing.

## 2. Errors and what to do next

Catch a category when the reaction is the same; catch a concrete class from
`auto_3dx.errors` when it differs.

| Category | Guarantee | Agent action |
|---|---|---|
| `SessionError` (`Com3dxNotFoundError`, `CatiaConnectionError`, `NoActiveEditorError`, `NoActivePartError`, `InactivePartError`) | Could not reach or use a session, or the Part is not the active one | Report it; ask the user to start 3DEXPERIENCE, open or activate the Part, or leave the Assembly context |
| `ValidationError` (`StaleSnapshotError`, `CrossBodyReferenceError`, `SupportNotUpdatedError`, `UnsupportedSupportError`, `ParameterTypeError`, ...) | Refused before any COM call; the model is untouched | Fix the arguments or context, per the table below |
| `NotFoundError` (`ParameterNotFoundError`, `SketchNotFoundError`, `SketchElementNotFoundError`, `TopologyQueryNoMatchError`, `FeatureNotFoundError`, `BodyNotFoundError`, `PlaneNotFoundError`, `ConstraintNotFoundError`, ...) | No object with that name, decided by enumeration | Re-list the current names and ask when unsure |
| `ConflictError` (`*AlreadyExistsError`, `FeatureConflictError`, `AmbiguousNameError`, `BodyRemovalError`, `TargetNotUpToDateError`, `ParameterInUseError`, `BooleanOperationError`, `TopologyQueryAmbiguousError`, `ReferenceInUseError`) | The model's names or state block the request; nothing was created or changed | Resolve per the table below |
| `AutomationError` | CATIA was called; the model may have changed. Carries `hresult` | Inspect before any further mutation |
| `PartUpdateError` | A rebuild failed and the model is invalid | Run the recovery procedure in §3 |
| `PartialCreationError` | Created, but the follow-up rename failed; a default-named object is left behind | Find it through `inspect.summary()` and remove it before retrying |

Specific errors and the correct response:

| Error | Response |
|---|---|
| `StaleSnapshotError` | Take a fresh topology snapshot and re-identify the target |
| `CrossBodyReferenceError` | Targeting mistake: snapshot the body you are building in (`part.topology.edges(body=...)`). Never bypass it |
| `SupportNotUpdatedError` | `part.update()`, then create the sketch on the plane |
| `TargetNotUpToDateError` | Rebuild the target (`body.update()` or `part.update()`), then measure |
| `SketchElementNotFoundError` | Re-read `sketch.element_names()`; the name changed or the element is gone |
| `ParameterInUseError` | Remove the dependent formula first, or get explicit intent for `force=True` |
| `BooleanOperationError` | Check the tool body: it must not be the target, from another Part, or already consumed |
| `UnsupportedSupportError` | An unsupported plane or axis (for example a circular-pattern axis other than `"Z"`) |
| `InactivePartError` | Activate the Part in CATIA and retry |
| `TopologyQueryNoMatchError` | The query's assumptions are wrong: read the candidate facts in the message and fix the criteria |
| `TopologyQueryAmbiguousError` | The intent is underspecified: add a criterion. Never fall back to `first()` or an index |
| `ReferenceInUseError` | A sketch still uses the plane: remove the feature, then the sketch, then the plane |

Warnings sit outside the hierarchy, so `except Auto3dxError` never catches one.
`SelectionNotRestoredWarning` (a `UserWarning`) is the only one; see §6.

## 3. Recovering from a failed update

`PartUpdateError` leaves the model invalid, and **every later rebuild fails until
it is repaired**. Nothing is rolled back or deleted automatically: the SDK cannot
know which change you meant to keep, and removing a pad cascades to its sketch.

**Read the diagnostics, but not as a cause.** `part.inspect.update_issues()` and
`PartUpdateError.issues` return `UpdateIssue` records (`name`, `kind`,
`body_name`, `up_to_date`, `active`) for every feature. They list **symptoms,
not the cause**: live, an invalid boss height flagged the fillet and pocket
downstream of the boss, not the boss itself, and a suppressed base pad showed as
inactive while its dependants showed as not up to date. The first dirty feature
is not necessarily the culprit, and `issues` is `()` when it could not be read.
Use them to see what is affected, then look at the most recent edit and the
history order. Never delete every listed object.

**Repair before deleting.** Distinguish the two cases:

**A. A reversible change to a model that was valid** — a dimension, parameter or
formula value, or a suppression you just applied.

1. Stop mutating.
2. Put the last known valid value or state back.
3. Rebuild again (`part.update()`, or `body.update()` for one body).
4. Confirm with `part.is_up_to_date()` / `body.is_up_to_date`.
5. Report what was rolled back and why.

Live evidence: a pad taken from 30 mm to 1 mm broke a dependent 5 mm fillet and
`part.update()` raised. Nothing was deleted; restoring 30 mm and updating again
healed the model with the fillet intact and the original volume. A fillet taken
from 4 mm to 8 mm and back behaved the same way, and a suppressed upstream pad
recovered by reactivating it.

**B. A newly created feature that never rebuilt**, an edit whose previous value
is unknown, or a rollback that itself failed.

1. Stop mutating.
2. Remove the offending feature with its `remove_*` method (a rectangular
   pattern has no name lookup: pass the wrapper to
   `remove_rectangular_pattern(pattern)`).
3. Rebuild to confirm a known-good state.
4. If it still fails, the broken feature is not the one you think. Inspect with
   `part.inspect.summary()` and report rather than removing things
   speculatively.

Never delete downstream features to force a change through. Not every update
failure is recoverable — report the outcome honestly instead of retrying the
same call unchanged.

## 4. Removal side effects

| Removal | Side effect |
|---|---|
| `remove_pad` | Also removes the Pad's sketch |
| `remove_pocket` | The sketch **stays**; remove it separately if you created it |
| `formulas.remove` | The target parameter keeps the last computed value |
| `parameters.remove` | Refused with `ParameterInUseError` while a formula reads it; `force=True` leaves an orphaned relation |
| `planes.remove(plane)` | Refused with `ReferenceInUseError` while a sketch uses the plane; `force=True` orphans the dependants. An angle plane's axis points and line stay; `remove_geometrical_set()` has the same guard |
| `bodies.remove(name, delete_contents=True)` | Deletes every feature and sketch in that body. Refused without the flag, and always refused for the main body (`BodyRemovalError`) |
| `remove_boolean(name, delete_consumed_body=True)` | **Destroys the consumed tool body permanently.** The target geometry returns; the tool body does not |
| `sketch.constraints.remove(...)` | Runs inside a sketch edition; indices of the remaining constraints shift, so never hold one |
| Any removal | Runs through the editor's selection, so the Part must be active |

Deleting an object you did not create in the current task needs explicit user
intent that names it. Prefer **suppression** over deletion when the user wants a
feature temporarily out of the way.

## 5. Names and model-backed identity

- The CATIA model is the source of truth. Rediscover bodies, sketches, sketch
  elements, parameters, formulas, features, patterns and constraints by name in
  every process; do not carry Python wrappers across processes.
- CATIA accepts duplicate names; the SDK refuses to create them and refuses
  ambiguous lookups. A name must be non-empty, without surrounding whitespace,
  and contain no `\`.
- `Parameter.name` may be qualified (`3D Shape1\WIDTH`); use `short_name` when
  matching what the user typed.
- In a formula body, use `part.formulas.relation_name(parameter)`.
- `ensure_*` reuses an existing object only when readable data proves it is the
  same. There is no `ensure` for planes, bodies, edge and face features, or
  patterns.
- A Part may hold `EnumParam` parameters; they read as strings, and writing them
  is unsupported.

## 6. Session side effects

- Topology searches and `part.inspect.summary()` capture the user's selection,
  search, restore it and check the count.
  - If the selection cannot be read, the snapshot is refused with
    `AutomationError` before anything changes.
  - If CATIA silently refuses part of the restore, the snapshot is returned and
    `SelectionNotRestoredWarning` is emitted. It is valid and the model is
    unchanged; only UI selection was lost. Keep it, tell the user, and do not
    rebuild the selection with raw `Selection` calls or silence the warning.
- Selection-based operations run only on the active Part (`InactivePartError`);
  `summary.topology` is `None` for a non-active Part.
- The In-Work Object is where CATIA puts the next feature. Read it with
  `part.inspect.in_work_object()`, never `part.com_object.InWorkObject`. Creating
  a feature moves it; `work_in(body)` and `work_at(feature)` set it for their
  block and restore the previous one on every exit, including on exception; a
  targeted `body.update()` does not move it. There is no public setter.
- `part.is_up_to_date()` and `body.is_up_to_date` are rebuild status only, not
  unsaved-change detectors.
- Everything runs on the main thread.

## 7. Operation classes

| Class | Examples | Rule |
|---|---|---|
| Read | `list`, `get`, `names`, `inspect`, `measure`, snapshots | Free to use |
| Model mutation | `create_*`, `ensure_*`, `set_*`, `activate`/`deactivate`, `remove_*`, `update`, visibility | In-session only; within the user's request |
| Irreversible mutation | `remove_boolean(..., delete_consumed_body=True)`, `bodies.remove(..., delete_contents=True)`, `parameters.remove(..., force=True)` | Explicit user intent naming what is destroyed |
| Persistence | Save, SaveAs, PLMPropagate, writing files | Not exposed by the SDK. The user does it in the UI |

A 3DEXPERIENCE save commits to the server and includes every unsaved change in
the session, not only this task's.

## 8. Raw COM

`wrapper.com_object` is the only escape hatch. It bypasses validation, generation
tracking and ownership checks, and a normal workflow never needs it.

- Allowed in ordinary work: read-only property reads the SDK documents as living
  behind `com_object`.
- Not allowed in ordinary work: any raw mutation, raw topology handling, raw save
  or export, reaching for `ShapeFactory`, `HybridShapeFactory`, `Selection`,
  `MeasurableService` / `MeasureService`,
  `win32com`, `com3dx` or private `_…` members, or passing a raw object to get
  around a `ValidationError` such as `CrossBodyReferenceError`. Use
  `catia.active_window_title` rather than reading the window through COM, and
  `sketch.constraints.remove(...)` rather than `Constraints.Remove` or
  `Selection.Delete`. Raw `PartDocument.ExportData` failed live on PLM-backed
  documents and left an unexplained extra editor; do not try it.
- Never select topology by index or by parsing `descriptor` strings; select by
  measured geometry through a semantic query (`geometry-query.md`).
- **If a public capability is missing, stop and report the SDK gap.** Raw
  Automation is appropriate only during explicit SDK-development or
  capability-probe work inside the auto-3dx repository.

## 9. Scratch and exploratory changes

When experimenting in a user's session: use distinctive names, wrap mutations in
`try/finally` that removes what was created, confirm cleanup by counting what
remains rather than trusting that a removal did not raise, and never save.
