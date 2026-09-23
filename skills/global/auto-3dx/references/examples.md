# auto-3dx usage patterns

A few high-value patterns against the current public API. Every `python` block
here is checked against the installed package by `scripts/validate_skill.py`.
Names such as `AGENT_PAD` are placeholders; pick names that do not collide with
the user's model.

Topology is always selected by **geometric intent** with `one()` — never by
index, never by parsing descriptors.

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

print(parameters.dependents("WIDTH"))        # formulas that read it, from the model
part.formulas.remove("WIDTH_DRIVER")         # remove the dependent formula first
parameters.remove("WIDTH")
```

## 3. A new feature: guarded update, then measure

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
design = part.part_design
before = part.measurement.measure()

sketch = part.sketches.create("AGENT_PAD_PROFILE", support="XY")
with sketch.edit() as editor:
    editor.rectangle(60.0, 40.0)        # four lines, no constraints added

pad = design.create_pad("AGENT_PAD", sketch, 12.0, unit="mm")
try:
    part.update()
except PartUpdateError:
    # This pad never built and there is nothing to roll back: removal is the repair.
    design.remove_pad("AGENT_PAD")      # also removes AGENT_PAD_PROFILE
    part.update()
    raise

after = part.measurement.measure()
print(pad.height, after.volume_mm3 - before.volume_mm3)
```

## 4. Update failure: read the issues, roll back the edit

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
boss = part.part_design.get_pad("BOSS")
previous = boss.height                  # the last known valid value

boss.set_height(1.0, unit="mm")
try:
    part.update()
except PartUpdateError as error:
    # Symptoms, not the cause: downstream features may be listed, not BOSS.
    for issue in error.issues:
        print(issue.name, issue.kind, issue.body_name, issue.up_to_date, issue.active)
    boss.set_height(previous, unit="mm")    # roll back the most recent edit
    part.update()                           # CATIA heals; nothing was deleted
    print(part.is_up_to_date())
    raise
```

## 5. The top face, by position — not by normal sign

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
faces = part.topology.faces(body="PartBody")

# Planar, normal along Z (either sign), then the highest along +Z.
top = faces.query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, 1)).one()
print(top.geometry.area_mm2, top.geometry.center_mm)

part.part_design.create_shell("AGENT_SHELL", top, internal_thickness=2.0,
                              external_thickness=0.0)
try:
    part.update()
except PartUpdateError:
    part.part_design.remove_shell("AGENT_SHELL")
    part.update()
    raise
```

## 6. A fillet target found by geometry

```python
from auto_3dx import Catia
from auto_3dx.errors import TopologyQueryAmbiguousError

part = Catia.attach().active_part()
body = part.bodies.get("AGENT_TOOL")
edges = part.topology.edges(body=body)

# A circular edge of radius ~6 mm whose centre is nearest the expected point.
rim = edges.query().circular().radius_near(6.0, 0.01).nearest((30.0, 0.0, 25.0)).one()

# A vertical straight edge near a known corner.
try:
    corner = edges.query().lines().parallel((0, 0, 1)).nearest((40.0, 25.0, 5.0)).one()
except TopologyQueryAmbiguousError:
    raise                               # the intent is underspecified: add a criterion

with part.work_in(body):
    part.part_design.create_edge_fillet("AGENT_RIM_FILLET", rim, radius=1.0)
body.update()
# The model changed: take a new snapshot and re-run the query before reusing it.
```

## 7. A pocket with explicit direction, verified by volume

```python
from auto_3dx import Catia
from auto_3dx.geometry.part_design import DIRECTION_ALONG_SKETCH_NORMAL

part = Catia.attach().active_part()
before = part.measurement.measure().volume_mm3

sketch = part.sketches.create("AGENT_HOLE_PROFILE", support="XY")
with sketch.edit() as editor:
    editor.circle(0.0, 0.0, 4.0)
pocket = part.part_design.create_pocket("AGENT_HOLE", sketch, 10.0,
                                        direction=DIRECTION_ALONG_SKETCH_NORMAL)
part.update()

removed = before - part.measurement.measure().volume_mm3
if removed <= 0.0:
    # Rebuilt fine, cut nothing: the direction was wrong for this sketch.
    pocket.reverse_direction()
    part.update()
    removed = before - part.measurement.measure().volume_mm3
print(pocket.direction, removed)
```

## 8. Edit a reference plane, then delete it safely

```python
from auto_3dx import Catia
from auto_3dx.errors import ReferenceInUseError

part = Catia.attach().active_part()
plane = part.planes.get("BOSS_PLANE")   # an offset plane; angle planes use set_angle
previous = plane.offset
plane.set_offset(8.0)                   # no rebuild here
part.update()                           # the sketch and boss on it regenerate
faces = part.topology.faces(body="PartBody")    # everything moved: fresh snapshot

print(part.planes.dependents(plane))    # sketches still built on the plane
try:
    part.planes.remove(plane)
except ReferenceInUseError:
    part.part_design.remove_pad("BOSS")  # removes the boss and its sketch
    part.update()
    part.planes.remove(plane)            # now nothing depends on it
print(previous)
```

## 9. Edit a model this process did not build

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

sketch = part.sketches.get("PROFILE")            # rediscover by name
print(sketch.element_names())
circle = sketch.get_element("Circle.1")          # SketchElementNotFoundError if gone
print(circle.kind, circle.radius)

fillet = part.part_design.get_edge_fillet("F1")
fillet.set_radius(8.0)                           # edit, never delete-and-recreate
hole = part.part_design.get_hole("H1")
hole.set_diameter(6.0)
part.update()                                    # one rebuild for the batch
```

## 10. Insert a feature at a chosen point in history

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
base = part.part_design.get_pad("BASE")
sketch = part.sketches.get("RIB_PROFILE")

with part.work_at(base):                 # the new pad lands right after BASE
    part.part_design.create_pad("RIB", sketch, 6.0)
part.update()
```

## 11. Model in another body, rebuild it, measure it

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
print(part.measurement.measure(body).volume_mm3)
```

## 12. A bolt circle, instead of duplicating holes by hand

```python
from auto_3dx import Catia

part = Catia.attach().active_part()

seed = part.part_design.get_pocket("BOLT_HOLE")
pattern = part.part_design.create_circular_pattern("BOLT_CIRCLE", seed, 6, 60.0)
part.update()                            # axis="Z" is the only verified axis

pattern.set_angular_instances(8)         # setters do not rebuild
part.update()
print(pattern.angular_instances, pattern.angular_spacing_deg)
```

## 13. A boolean, whose tool body is consumed for good

```python
from auto_3dx import Catia

part = Catia.attach().active_part()
housing = part.bodies.get("AGENT_HOUSING")
core = part.bodies.get("AGENT_TOOL")

with part.work_in(housing):              # the work body is the target
    cut = part.part_design.create_boolean_remove("CUT_CORE", core)
part.update()

# AGENT_TOOL is consumed: gone from part.bodies, and it does not come back.
print(cut.operation, cut.tool_body_name, part.bodies.names())
```

## 14. Suppress a feature instead of deleting it

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().active_part()
pad = part.part_design.get_pad("BASE")

pad.deactivate()                         # the feature stays in the tree
try:
    part.update()
except PartUpdateError as error:
    # Dependants show as not up to date; the cause is this suppression.
    print([issue.name for issue in error.issues])
    pad.activate()
    part.update()
    raise
# Any topology snapshot taken before this is stale: take a fresh one.
```
