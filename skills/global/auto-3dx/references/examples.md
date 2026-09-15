# auto-3dx usage patterns

Small, generic patterns written against the current public API. Every
`python` block here is checked against the installed package by
`scripts/validate_skill.py`. Names such as `AGENT_PAD` are placeholders; pick
names that do not collide with the user's model.

## 1. Attach, choose the Part, inspect

```python
from auto_3dx import Catia

catia = Catia.attach()

for info in catia.editors():
    print(info.name, info.object_kind, info.object_name, info.is_part)

part = catia.part_named("MY_PART")      # catia.active_part() when only one Part is open
summary = part.inspect.summary()
print(summary.render())

for feature in summary.features:
    if not feature.supported:
        print(f"{feature.name} is a {feature.kind}; auto-3dx cannot edit that kind")
```

## 2. Read and change a parameter

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
parameters = part.parameters

print(parameters.user_names())
width = parameters.get("WIDTH")         # NotFoundError / AmbiguousNameError: ask, do not guess
print(width.short_name, width.kind, width.value, width.unit)

parameters.set("WIDTH", 80.0, unit="mm")        # a value write: no rebuild, snapshots go stale
offset = parameters.ensure_length("AGENT_OFFSET", 5.0)   # creates, or updates the same kind
part.update()
print(parameters.get("WIDTH").value, offset.value)
```

## 3. Sketch geometry with constraints

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

sketch = part.sketches.create("AGENT_SKETCH", support="XY")
with sketch.edit() as editor:
    base = editor.line(0.0, 0.0, 60.0, 0.0)
    side = editor.line(60.0, 0.0, 60.0, 40.0)
    editor.horizontal(base)
    editor.perpendicular(base, side)
    editor.length(base, 60.0, unit="mm")
# `editor` is closed here; constraints can only be created inside the block.
part.update()
print(sketch.constraints.names(), sketch.constraints.broken_count)
```

## 4. A feature with a guarded update and a measured result

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
design = part.part_design
before = part.measurement.measure()     # assumes the main body already holds a solid

sketch = part.sketches.create("AGENT_PAD_PROFILE", support="XY")
with sketch.edit() as editor:
    editor.rectangle(60.0, 40.0)

pad = design.create_pad("AGENT_PAD", sketch, 12.0, unit="mm")
try:
    part.update()
except PartUpdateError:
    design.remove_pad("AGENT_PAD")      # also removes AGENT_PAD_PROFILE
    part.update()                       # confirms the model rebuilds again
    raise

after = part.measurement.measure()
print(pad.height, after.volume_mm3 - before.volume_mm3)
```

## 5. Reacquire topology before every topology-consuming call

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
design = part.part_design

edges = part.topology.edges()           # the whole solid, valid for this generation only
edge = edges[0]                         # a position in this snapshot, not a semantic choice
print(len(edges), edge.descriptor)      # descriptor is for logging only

design.create_edge_fillet("AGENT_FILLET", edge, radius=2.0, unit="mm")
try:
    part.update()
except PartUpdateError:
    design.remove_edge_fillet("AGENT_FILLET")
    part.update()
    raise

# `edges` is stale now: using edges[1] would raise StaleSnapshotError before
# CATIA is touched. Take a new snapshot and identify the target again.
faces = part.topology.faces()
design.create_shell("AGENT_SHELL", faces[0], internal_thickness=2.0, external_thickness=0.0)
try:
    part.update()
except PartUpdateError:
    design.remove_shell("AGENT_SHELL")
    part.update()
    raise
```

## 6. Drive a dimension from a parameter

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

driver = part.parameters.ensure_length("AGENT_THICKNESS", 12.0)
pad = part.part_design.get_pad("AGENT_PAD")
body = f"{part.formulas.relation_name(driver)} * 2"     # never build a body from Parameter.name
part.formulas.ensure("AGENT_PAD_HEIGHT", pad.depth_parameter(), body)
part.update()
print(pad.height)                       # now follows AGENT_THICKNESS
```
