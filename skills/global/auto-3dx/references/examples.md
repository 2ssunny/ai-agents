# auto-3dx usage patterns

A few high-value patterns against the current public API. Every `python` block
here is checked against the installed package by `scripts/validate_skill.py`.
Names such as `AGENT_PAD` are placeholders; pick names that do not collide with
the user's model.

## 1. Attach, confirm the document, inspect

```python
from auto_3dx import Catia

catia = Catia.attach()
print(catia.active_window_title)        # confirm the right document, no raw COM

part = catia.part_named("MY_PART")      # catia.active_part() when only one is open
summary = part.inspect.summary()
print(summary.render())

for body in summary.bodies:
    print(body.name, body.is_main, len(body.features), len(body.sketches))
in_work = summary.in_work_object
if in_work is not None and not in_work.is_main_body:
    print(f"In-Work Object is {in_work.name} ({in_work.kind})")
```

## 2. Parameters, and removing one a formula depends on

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
parameters = part.parameters

print(parameters.user_names())
width = parameters.get("WIDTH")
print(width.short_name, width.kind, width.value, width.unit)

parameters.set("WIDTH", 80.0, unit="mm")     # a value write: no rebuild
part.update()

# A parameter a formula reads is protected; remove the formula first.
print(parameters.dependents("WIDTH"))        # [Formula(...)] straight from the model
part.formulas.remove("WIDTH_DRIVER")
parameters.remove("WIDTH")
```

## 3. Sketch constraints, including removing one

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

sketch = part.sketches.create("AGENT_SKETCH", support="XY")
with sketch.edit() as editor:
    base = editor.line(0.0, 0.0, 60.0, 0.0)
    side = editor.line(60.0, 0.0, 60.0, 40.0)
    editor.horizontal(base)
    editor.perpendicular(base, side)
part.update()

print(sketch.constraints.names())
sketch.constraints.remove("Perpendicularity.1")   # public API only
part.update()
```

## 4. A new feature: guarded update, then measure

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
design = part.part_design
before = part.measurement.measure()

sketch = part.sketches.create("AGENT_PAD_PROFILE", support="XY")
with sketch.edit() as editor:
    editor.rectangle(60.0, 40.0)

pad = design.create_pad("AGENT_PAD", sketch, 12.0, unit="mm")
try:
    part.update()
except PartUpdateError:
    # This pad never built and there is nothing to roll back, so removal is the repair.
    design.remove_pad("AGENT_PAD")      # also removes AGENT_PAD_PROFILE
    part.update()
    raise

after = part.measurement.measure()
print(pad.height, after.volume_mm3 - before.volume_mm3)
```

## 5. Repair a model an edit made invalid

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
pad = part.part_design.get_pad("AGENT_PAD")
previous = pad.height                   # the last known valid value

pad.set_height(1.0, unit="mm")          # an upstream dimension a fillet depends on
try:
    part.update()
except PartUpdateError:
    # Nothing was deleted. Roll the edit back; CATIA heals the model and the
    # dependent fillet survives. Deletion would be the wrong first move.
    pad.set_height(previous, unit="mm")
    part.update()
    print(part.is_up_to_date())
    raise
```

## 6. Edit a model this process did not build

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

# Rediscover by name; handles from an earlier process are worthless.
sketch = part.sketches.get("PROFILE")
print(sketch.element_names())
circle = sketch.get_element("Circle.1")          # SketchElementNotFoundError if gone
print(circle.kind, circle.radius)

fillet = part.part_design.get_edge_fillet("F1")
previous = fillet.radius
fillet.set_radius(8.0)                           # edit, never delete-and-recreate
hole = part.part_design.get_hole("H1")
hole.set_diameter(6.0)
hole.set_depth(12.0)
part.update()                                    # one rebuild for the batch
print(previous, fillet.radius, hole.diameter)
```

## 7. Insert a feature at a chosen point in history

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
base = part.part_design.get_pad("BASE")
sketch = part.sketches.get("RIB_PROFILE")

with part.work_at(base):                 # the new pad lands right after BASE
    part.part_design.create_pad("RIB", sketch, 6.0)
part.update()
print([feature.name for feature in part.inspect.features()])
```

## 8. Model in another body, rebuild it, measure it

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

body = part.bodies.create("AGENT_TOOL")
with part.work_in(body):
    sketch = part.sketches.create("AGENT_TOOL_PROFILE", support="XY")
    with sketch.edit() as editor:
        editor.rectangle(40.0, 30.0)
    part.part_design.create_pad("AGENT_TOOL_PAD", sketch, 20.0, unit="mm")

body.update()                            # leaving the block rebuilds nothing
print(body.is_up_to_date)
print(part.measurement.measure(body).volume_mm3)
```

## 9. Body-scoped topology, then a feature in that body

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
design = part.part_design
body = part.bodies.get("AGENT_TOOL")

with part.work_in(body):
    edges = part.topology.edges()        # follows the work body
    solid_edges = [
        edge for edge in edges
        if edge.owner_feature_name == "AGENT_TOOL_PAD"   # skip sketch wire edges
    ]
    design.create_edge_fillet("AGENT_TOOL_FILLET", solid_edges[0], radius=2.0)

try:
    body.update()
except PartUpdateError:
    design.remove_edge_fillet("AGENT_TOOL_FILLET")
    body.update()
    raise
```

## 10. A bolt circle, instead of duplicating holes by hand

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

seed = part.part_design.get_pocket("BOLT_HOLE")
pattern = part.part_design.create_circular_pattern("BOLT_CIRCLE", seed, 6, 60.0)
part.update()                            # axis="Z" is the only verified axis

pattern.set_angular_instances(8)         # setters do not rebuild
pattern.set_angular_spacing_deg(45.0)
part.update()
print(pattern.angular_instances, pattern.angular_spacing_deg, pattern.radial_instances)
```

## 11. A boolean, whose tool body is consumed for good

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
housing = part.bodies.get("AGENT_HOUSING")
core = part.bodies.get("AGENT_TOOL")

with part.work_in(housing):              # the work body is the target
    cut = part.part_design.create_boolean_remove("CUT_CORE", core)
part.update()

# AGENT_TOOL is now consumed: it is gone from part.bodies and does not come back.
print(cut.operation, cut.tool_body_name, part.bodies.names())
```

## 12. Suppress a feature instead of deleting it

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
fillet = part.part_design.get_edge_fillet("F1")

fillet.deactivate()                      # the feature stays in the tree
try:
    part.update()
except PartUpdateError:
    # A downstream feature depended on it: reactivate and rebuild, never delete.
    fillet.activate()
    part.update()
    raise
print(fillet.is_active)
# Any topology snapshot taken before this is now stale: take a fresh one.
```
