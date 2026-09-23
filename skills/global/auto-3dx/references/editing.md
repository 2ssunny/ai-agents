# Editing an existing model

How to change a model the agent did not build. Upstream contract:
`docs/api-design.md` section 17. Everything here reads the model rather than
remembering Python objects.

## Feature dimensions

Edit in place. Do **not** delete and recreate a feature to change a dimension
that is editable — recreating re-resolves the edges or faces it consumes.

```python
fillet = part.part_design.get_edge_fillet("F1")
previous = fillet.radius          # keep the old value for rollback
fillet.set_radius(8.0)            # no rebuild happens here
part.update()
```

Verified editable dimensions, live-tested end to end (read, write, rebuild,
geometry change, re-read from a fresh wrapper):

| Feature | Read | Write |
|---|---|---|
| `ConstRadEdgeFillet` | `radius` | `set_radius(value, unit="mm")`, `radius_parameter()` |
| `Chamfer` | `length1`, `angle` | `set_length1(...)`, `set_angle(..., unit="deg")` |
| `Hole` | `diameter`, `depth` | `set_diameter(...)`, `set_depth(...)` |
| `Shell` | `internal_thickness`, `external_thickness` | `set_internal_thickness(...)`, `set_external_thickness(...)` |
| `Thickness` | `offset` | `set_offset(...)` |
| `Pad` / `Pocket` | `depth` (`Pad.height`) | `set_depth(...)` / `set_height(...)` |
| `Shaft` / `Groove` | `first_angle`, `second_angle` | `set_first_angle(...)`, `set_second_angle(...)` |

Setters validate, advance the generation, and **do not rebuild**, so several
edits batch into one `part.update()`. Measuring before that rebuild correctly
fails with `TargetNotUpToDateError`.

**Not editable** (verified absent, not merely untried):

- `Chamfer` Length2 — CATIA refused the write in the mode this SDK creates.
- A generic `Hole.Depth` member does not exist; the verified path is the bottom
  limit, which `depth` / `set_depth` already use.
- Generic `Thickness.Thickness` / `.Value` members do not exist; the member is
  `offset`.
- Rectangular pattern dimensions and multi-sections solid dimensions.

## Rediscovering sketch elements

The name CATIA gives an element is its durable identity; a collection index is
not, and a Python handle from an earlier process is worthless.

```python
sketch = part.sketches.get("PROFILE")     # drawn by an earlier process
sketch.element_names()                    # ['AbsoluteAxis', 'Line.1', 'Circle.1']
line = sketch.get_element("Line.1")       # SketchElementNotFoundError if absent
for element in sketch.elements():
    print(element.name, element.kind)
```

A rediscovered `SketchElement` carries `name`, `kind` and its owning sketch, so
it goes straight back into the constraint methods — which still require an open
`with sketch.edit()` block. Reading does not.

- `radius` is exposed for circles because it reads live.
- **Line coordinates are not exposed**: this release's `Line2D` has no
  coordinate members. Do not claim a coordinate getter exists.
- Live-verified rediscovered kinds include `Line2D`, `Circle2D` and the sketch
  axis.

## Choosing the history position: `work_at`

```python
with part.work_at(part.part_design.get_pad("BASE")):
    part.part_design.create_pad("RIB", sketch, 6.0)   # lands right after BASE
part.update()
```

- `work_in(body)` chooses **which body** to model in; `work_at(feature)` chooses
  **where in that body's history** the next feature goes.
- Live: a tree of `PAD, FILLET`, working at `PAD`, produced `PAD, NEW, FILLET`.
  CATIA inserts immediately after the In-Work feature. **No existing feature
  moves** — this is not tree reordering.
- It takes a feature wrapper from `part.part_design`, never a raw COM object and
  never a body. A feature from another Part is refused.
- The exact previous In-Work Object is restored on every exit: normal return,
  Python exception, or Automation failure. The two contexts nest, and the
  innermost one decides.

## Reference planes

Offset and angle planes are editable in place, and the sketches and features on
them follow the next rebuild.

```python
plane = part.planes.create_offset("BOSS_PLANE", support="XY", offset=10.0)
part.update()
previous = plane.offset
plane.set_offset(8.0)            # AnglePlane has angle / set_angle(degrees)
part.update()                    # the sketch on it and its features regenerate
```

- `part.planes.get(name)` finds a plane again in a fresh process. Check its kind
  before editing: an offset plane has `offset` / `set_offset`, an angle plane
  `angle` / `set_angle`.
- Setters do not rebuild. If the rebuild fails, restore the previous value and
  update again before touching any downstream geometry.
- Reacquire topology after a plane edit: everything built on the plane moved.

### Deleting a plane safely

CATIA lets a plane be deleted while a sketch still uses it, orphaning the sketch
and every feature on it so the next rebuild fails. The SDK refuses by default:

```python
part.planes.dependents(plane)    # ['BOSS_SK'] -- sketches on this plane
part.planes.remove(plane)        # ReferenceInUseError while a sketch uses it
```

Preferred lifecycle: remove the downstream feature, then its sketch, then the
plane. `remove(plane, force=True)` (and `remove_geometrical_set(force=True)`)
deletes anyway and leaves the dependants failing — only with explicit intent to
orphan them. Dependency is found by comparing sketch frames with the plane
frame, so a sketch on a different plane with an identical frame also counts;
the guard errs towards refusing.

## Parameters a formula depends on

```python
part.parameters.dependents("L_box")    # [Formula(name='DriveL')] — asks the model
part.parameters.remove("L_box")        # ParameterInUseError; nothing changed
part.formulas.remove("DriveL")         # remove the dependent formula first
part.parameters.remove("L_box")        # now it is safe
```

CATIA would otherwise remove the parameter silently and rewrite the formula body
to `deleted_L_box * 2`, leaving an orphaned relation and a Part that is no longer
up to date. The guard asks each formula for its own inputs through Automation
(`Formula.GetInParameter`), so it works in any process and never parses formula
text. `part.formulas.reading(parameter)`, `Formula.inputs()` and
`Formula.reads(parameter)` expose the same information.

`remove(name, force=True)` accepts the orphan deliberately — only with explicit
user intent.

**Limitation.** Only formulas are covered. `Relations` can also hold rules,
checks, laws, programs and design tables, none of which expose a verified input
list, so a parameter used only by one of those is not reported as in use.
