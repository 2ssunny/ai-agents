# auto-3dx safety semantics

Detail behind the rules in `SKILL.md`. Upstream source of truth:
`docs/api-design.md` in the auto-3dx repository (sections 5, 6, 7, 8, 9, 12, 15).

## 1. Model generation

Each CATIA Part has one generation counter, shared by every `Part` wrapper of
that Part (matched by COM identity) and by every collection and wrapper reached
through them. Topology snapshots are stamped with it and refused once it moves.

| Operation through the SDK | Advances |
|---|---|
| Creating any feature, sketch, plane, parameter or formula | yes |
| Removing any of them | yes |
| Writing a value: parameter `set`, `set_height` / `set_depth` / `set_*_angle`, constraint `set_value` | yes |
| `ensure_*` that writes to an existing object | yes |
| Renaming, activating, deactivating or modifying a formula | yes |
| Closing a `sketch.edit()` block (once per block) | yes |
| `part.update()`, success **or** failure | yes |
| A call that raised after reaching CATIA | yes — it advances on attempt |
| A `ValidationError` raised before any COM call | no |
| Reads: `list`, `get`, `names`, measurement, inspection, taking a snapshot | no |

Consequences:

- A parameter write stales snapshots even when the parameter drives nothing.
- Changes made in the CATIA UI or by another script do not advance it.
- A rebuild through one wrapper stales snapshots taken through another wrapper
  of the same Part, whether it came from `active_part()`, `part_named()`,
  `parts()` or a separate `Catia.attach()`. Re-reading the Part is safe.

## 2. Errors and what to do next

Catch a category when the reaction is the same; catch a concrete class from
`auto_3dx.errors` when it differs.

| Category | Guarantee | Agent action |
|---|---|---|
| `SessionError` (`Com3dxNotFoundError`, `CatiaConnectionError`, `NoActiveEditorError`, `NoActivePartError`) | Could not reach or use a session | Report it; ask the user to start 3DEXPERIENCE, open the Part, or switch from an Assembly to a Part editor |
| `ValidationError` (including `StaleSnapshotError`) | Refused before any COM call; the model is untouched | Fix the arguments or context. For staleness, take a new snapshot and re-identify the target |
| `NotFoundError` | No object with that name, decided by enumeration | Check names with `names()` or `inspect.summary()`; ask when unsure |
| `ConflictError` (`*AlreadyExistsError`, `FeatureConflictError`, `SketchSupportMismatchError`, `AmbiguousNameError`) | The model's names or state block the request; nothing was created | Resolve with the user; never rename or delete the existing object to make room unless asked |
| `AutomationError` | CATIA was called; the model may have changed. Carries `hresult` | Inspect before any further mutation |
| `PartUpdateError` | The rebuild failed | Run the recovery procedure below |
| `PartialCreationError` | Created, but the follow-up rename failed; a default-named object is left behind | Find it through `inspect.summary()` and remove it before retrying |

Warnings sit outside this hierarchy, so `except Auto3dxError` never catches one.
`SelectionNotRestoredWarning` (a `UserWarning`) is the only one; see section 6.

## 3. Recovering from a failed update

A failed `Part.Update()` leaves the offending feature in the model, and **every
later update fails until it is removed**. Unrelated-looking follow-up failures
usually come from this.

1. Stop issuing mutations.
2. Remove the feature you just created with its `remove_*` method
   (`remove_pad`, `remove_edge_fillet`, ...). A rectangular pattern has no
   name lookup: pass the wrapper to `remove_rectangular_pattern(pattern)`.
3. Call `part.update()` again. Success means a known-good state is restored.
4. If it still fails, the broken feature is not the one you think. Inspect
   with `part.inspect.summary()` and report to the user rather than removing
   things speculatively.
5. Report what failed and what was removed. Do not retry the same call
   unchanged.

The SDK never rolls back on its own, because removal cascades (below) make
automatic rollback more dangerous than reporting.

## 4. Removal side effects

| Removal | Side effect |
|---|---|
| `remove_pad` | Also removes the Pad's sketch |
| `remove_pocket` | The sketch **stays**; remove it separately if you created it |
| `formulas.remove` | The target parameter keeps the last computed value |
| `planes.remove(plane)` | An angle plane's two axis points and axis line stay; `remove_geometrical_set()` removes everything the collection created, including planes you did not create in this task |
| Any removal | Runs through the editor's selection |

Deleting an object you did not create in the current task needs explicit user
intent that names it.

## 5. Names

- CATIA accepts duplicate names; the SDK refuses to create them and refuses
  ambiguous lookups. Do not work around this by renaming user objects.
- A name must be non-empty, have no surrounding whitespace, and contain no `\`.
- `Parameter.name` may be qualified (`3D Shape1\WIDTH`); use `short_name` to
  display and match what the user typed.
- In a formula body, use `part.formulas.relation_name(parameter)`; a body built
  from `Parameter.name` breaks.
- `ensure_*` reuses an existing object only when readable data proves it is the
  same (for example a pad on the same sketch); otherwise it raises a
  `ConflictError`. Where no such proof exists (planes, edge and face features,
  patterns) there is no `ensure`.

## 6. Session side effects

- `part.topology.edges()` / `faces()`, and `part.inspect.summary()` which counts
  topology through them, capture the user's CATIA selection, search, restore the
  selection and check its count.
  - If the selection cannot be read, the snapshot is refused with
    `AutomationError` before anything changes. There is nothing to clean up.
  - If CATIA silently refuses part of the restore (live: a Pad re-added after
    its own faces), the snapshot is returned and `SelectionNotRestoredWarning`
    is emitted. The snapshot is valid and the model is unchanged; only UI
    selection state was lost. Keep using the snapshot, do not retake it to
    "fix" the selection, do not rebuild the selection with raw `Selection`
    calls, and tell the user they may need to re-select in the UI. Record the
    warning rather than silencing it with a blanket filter.
- Inspection does not advance the generation and leaves the In-Work Object as
  it found it. `summary.topology` is `None` for a Part without an editor
  selection (built directly from a raw object).
- The In-Work Object is where CATIA puts the next feature. Read it with
  `part.inspect.in_work_object()` (`name`, `kind`, `is_main_body`, or `None`),
  not through `part.com_object.InWorkObject`. SDK operations move it: creating a
  pad makes the new pad the In-Work Object, creating a plane hands it back to
  the main body, and removing features does not restore the previous one. There
  is no public setter; do not assign it through raw COM. If it points somewhere
  unexpected before a feature task, report it rather than moving it.
- `part.is_up_to_date()` is rebuild status only: a standalone parameter change
  leaves it `True`. It is not an unsaved-changes detector.
- Everything runs on the main thread.

## 7. Operation classes

| Class | Examples | Rule |
|---|---|---|
| Read | `list`, `get`, `names`, `inspect`, `measure`, snapshots | Free to use |
| Model mutation | `create_*`, `ensure_*`, `set*`, `remove_*`, `update` | In-session only; within the user's request |
| Persistence | Save, SaveAs, PLMPropagate, writing or overwriting files | Not exposed by the SDK. The user does it in the UI |

A 3DEXPERIENCE save commits to the server and includes every unsaved change in
the session, not only this task's.

## 8. Raw COM

`wrapper.com_object` is the only escape hatch. It bypasses validation,
generation tracking and ownership checks, and a normal workflow never needs it.

- Allowed in ordinary work: read-only property reads the SDK documents as
  living behind `com_object`, such as a `SketchElement`'s radius or a point's
  coordinates.
- Not allowed in ordinary work: any raw mutation, raw topology handling, raw
  save or export, or passing a raw object to get around a `ValidationError`.
  Raw `PartDocument.ExportData` in particular failed live on PLM-backed
  documents and left an unexplained extra editor in the session; do not try it.
- Raw exploration of missing capabilities belongs in the auto-3dx repository's
  probe workflow, and only when the user is explicitly developing the SDK.

## 9. Scratch and exploratory changes

When experimenting in a user's session: use distinctive names, wrap mutations
in `try/finally` that removes what was created, confirm cleanup by counting
what remains rather than trusting that a removal did not raise, and never save.
