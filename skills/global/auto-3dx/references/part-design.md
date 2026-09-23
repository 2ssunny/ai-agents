# Part Design operations

Pad and Pocket direction, patterns, multi-body booleans, constraint removal and
feature suppression. Upstream contract: `docs/api-design.md` sections 18–19.

## Pad and Pocket direction

```python
from auto_3dx.geometry.part_design import (
    DIRECTION_ALONG_SKETCH_NORMAL, DIRECTION_AGAINST_SKETCH_NORMAL,
)
cut = part.part_design.create_pocket("HOLE", sketch, 20.0,
                                     direction=DIRECTION_ALONG_SKETCH_NORMAL)
cut.direction                   # read back from the model
cut.set_direction(DIRECTION_AGAINST_SKETCH_NORMAL)
cut.reverse_direction()         # neither setter rebuilds
```

- `create_pad` and `create_pocket` take `direction=None` by default, which keeps
  CATIA's own default: **along** the sketch normal for a Pad, **against** it for a
  Pocket. `Pad` and `Pocket` both expose `direction`, `set_direction()` and
  `reverse_direction()`. `ensure_pad` / `ensure_pocket` take no direction.
- **The zero-effect pocket trap.** A pocket sketched on XY under a block cuts
  downward into nothing by default; it creates, rebuilds successfully, and
  removes **0 mm³**. A successful rebuild does not prove the cut happened.
- When direction matters, pass it explicitly and **verify by volume** (or by a
  semantic query) that material was removed or added. Do not reverse a feature
  through an offset-plane workaround.
- Direction control covers Pad and Pocket only — not Shaft, Groove or Rib.

## Circular pattern

Use this instead of duplicating a hole by hand around a bolt circle.

```python
seed = part.part_design.get_pocket("BOLT_HOLE")
pattern = part.part_design.create_circular_pattern("BOLT_CIRCLE", seed, 6, 60.0)
part.update()

pattern.set_angular_instances(8)        # no rebuild here either
part.update()
```

- Signature: `create_circular_pattern(name, feature, angular_instances,
  angular_spacing_deg, axis="Z")`.
- Lifecycle: `circular_patterns`, `get_circular_pattern(name)`,
  `remove_circular_pattern(name)`. Patterns are found again by name in a fresh
  process.
- Editable: `angular_instances` / `set_angular_instances`,
  `angular_spacing_deg` / `set_angular_spacing_deg`. Setters do not rebuild.
- `radial_instances` is **read-only**: this SDK always creates one radial row.
- The seed feature must belong to the body being patterned in, checked with the
  same ownership machinery as topology (`CrossBodyReferenceError`).

**Axis: only `"Z"` is supported.** Passing the XY plane as both rotation centre
and axis patterned around Z and removed exactly the expected material; the other
two origin planes rotated about something the test geometry could not identify.
`axis` therefore accepts `"Z"` and refuses anything else with
`UnsupportedSupportError`. Do not assume `"X"` or `"Y"`.

## Multi-body booleans

All four operations are live-verified with exact volumes. The **target** is the
body being worked in; the **tool** is the body passed in.

```python
with part.work_in(housing):                         # housing is the target
    cut = part.part_design.create_boolean_remove("CUT_CORE", core_body)
part.update()

cut.operation          # the operation kind
cut.tool_body_name     # 'core_body', still readable from the model
```

`create_boolean_remove`, `create_boolean_add`, `create_boolean_intersect` and
`create_boolean_assemble` each take `(name, tool_body)`, by wrapper or by name.
Lifecycle: `boolean_operations`, `get_boolean(name)`, `remove_boolean(name)`.

Refused with `BooleanOperationError`, before CATIA is called, when the tool body
is the target itself, belongs to another Part, or has already been consumed.

### The tool body is consumed — this is not reversible

After the operation the tool body reports `InBooleanOperation` and **disappears
from `part.bodies`**. `BooleanOperation.tool_body_name` is how its name stays
readable, in any process.

Deleting the boolean restores the target geometry but **does not bring the tool
body back** — live, it did not return and its name could no longer be found. So
removal makes the caller say so:

```python
part.part_design.remove_boolean("CUT_CORE", delete_consumed_body=True)
```

This is the one place in the SDK where removing a feature destroys something
else. Rules for an agent:

- A consumed tool body is **not** a temporary, reversible input.
- Never casually delete a boolean expecting CATIA to restore the original body.
- If the tool solid may be needed later, model it so it survives — duplicate the
  geometry or defer the boolean — **before** consuming it.
- Deleting a boolean needs explicit user intent naming what will be lost.

## Removing a sketch constraint

```python
sketch.constraints.remove("Parallelism.1")    # or a Constraint from the collection
part.update()
```

`Constraints.Remove` takes an index and removing one renumbers the rest, so the
collection is enumerated and matched by the constraint or its name — never by an
index a caller holds. The removal runs inside a sketch edition; inside an open
`with sketch.edit()` block that session is reused rather than nested, and the
edition is always closed.

Use only `sketch.constraints.remove(...)`. Do not call `Constraints.Remove` or
`Selection.Delete` directly. Fresh-process rediscovery and removal is verified.

## Feature suppression

`is_active`, `activate()` and `deactivate()` are on every Part Design feature
wrapper. Suppression **does not delete** the feature — prefer it to deletion when
the user wants a feature temporarily out of the way.

```python
fillet.deactivate()
part.update()          # the fillet's material comes back; the feature stays
fillet.activate()
part.update()          # and the filleted volume returns exactly
```

- Live-tested on Pad, Pocket and Fillet.
- Like every other setter, these do not rebuild; call `part.update()` yourself.
- Suppression changes the solid, so it **advances the model generation**: a
  topology snapshot taken before it is refused with `StaleSnapshotError`. Never
  reuse a snapshot across a suppression or activation.

**Upstream suppression can break the model.** Suppressing a feature that later
features depend on makes the next rebuild fail — live, suppressing a pad under a
fillet did exactly that, leaving the Part not up to date with everything still in
the tree. The SDK does not predict which suppressions are safe. Recover the
reversible way:

1. Suppress, then attempt the update.
2. If the update fails, activate the feature again.
3. Update again and confirm with `part.is_up_to_date()`.
4. Do **not** delete downstream features to make a suppression stick.

`part.inspect.update_issues()` after such a failure shows the suppressed feature
as inactive and its dependants as not up to date. The dependants are symptoms;
the cause is the suppression you just made. Do not treat the first dirty
feature as the culprit (safety.md §3).
