# Geometry facts and semantic queries

How to say *which* face or edge a command acts on. Upstream contract:
`docs/api-design.md` section 19. This is the default way to select topology:

```text
engineering intent -> semantic query -> strict cardinality (one()) -> operation
```

Never `faces[0]`, never `edges[3]`, never parsing `descriptor` strings. Indices
and descriptors remain available for diagnostics only.

## Measured facts

Every `Face` and `Edge` from a snapshot has a lazy `geometry` property, measured
once per handle, read-only, and not advancing the generation.

**`face.geometry`** (`FaceGeometry`):

| Field | Meaning |
|---|---|
| `surface_type` | `"planar"`, `"cylindrical"` or `"unknown"` |
| `area_mm2` | Area in mm² (the SDK converts CATIA's m²; do not convert again) |
| `center_mm` | Centre of gravity, mm |
| `perimeter_mm` | Perimeter, mm |
| `normal` | Planar only: unit **plane** normal — **its sign is not outward** |
| `plane_origin_mm` | Planar only: a point on the plane |
| `radius_mm` | Cylindrical only |

**`edge.geometry`** (`EdgeGeometry`):

| Field | Meaning |
|---|---|
| `curve_type` | `"line"`, `"circle"`, `"arc"` or `"unknown"` |
| `length_mm`, `start_mm`, `mid_mm`, `end_mm` | Length and points, mm |
| `direction` | Line only: unit vector start → end |
| `radius_mm`, `center_mm`, `angle_deg` | Circle and arc only |

Units are already normalised; never apply raw CATIA unit conversion yourself.
Classification is only what CATIA answers: cones, spheres, tori, splines and
B-surfaces are `"unknown"`, never guessed.

## Plane normals are not outward normals

**This is a safety rule.** CATIA's measured plane normal is the orientation of
the supporting plane, not the outward direction of the solid. Live, the top
*and* the bottom face of a block both reported +Z.

Never reason `normal ≈ +Z → top face`. Use the normal only as an **axis**, and
decide top or bottom by **position**:

```python
faces = part.topology.faces(body="PartBody")
top = faces.query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, 1)).one()
bottom = faces.query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, -1)).one()
```

`normal_parallel` accepts either sign; `extreme` picks the spatial extreme.

## Queries

`snapshot.query()` on a `FaceSnapshot` or `EdgeSnapshot` returns an immutable
query: every step returns a new query, so a partial query can be reused.

| Step | Face query | Edge query |
|---|---|---|
| Type | `of_type(surface_type)`, `planar()`, `cylindrical()` | `of_type(curve_type)`, `lines()`, `circular()` (circle or arc) |
| Orientation | `normal_parallel(axis, tolerance_deg=1.0)` | `parallel(axis, tolerance_deg=1.0)` |
| Size | `radius_near(radius_mm, tolerance_mm=0.001)`, `area_between(minimum_mm2=None, maximum_mm2=None)`, `largest(tolerance_mm2=0.001)`, `smallest(...)` | `radius_near(radius_mm, tolerance_mm=0.001)`, `length_between(minimum_mm=None, maximum_mm=None)`, `longest(tolerance_mm=0.001)`, `shortest(...)` |
| Position | `nearest(point, tolerance_mm=0.001)`, `extreme(direction, tolerance_mm=0.001)` | same; a circle's position is its centre, other edges their midpoint |
| Owner | `owned_by(feature_name)` — **current** owner, not provenance | same |
| Result | `one()`, `first()`, `all()`, `count()`, `len(query)` | same |

```python
edges = part.topology.edges(body="PartBody")
rim = edges.query().circular().radius_near(6.0, 0.01).nearest((30.0, 0.0, 25.0)).one()
corner = edges.query().lines().parallel((0, 0, 1)).nearest((40.0, 25.0, 5.0)).one()
bore = part.topology.faces(body="PartBody").query().cylindrical().radius_near(6.0, 0.01).one()
```

- Tolerances are explicit, with the defaults shown. Rankings (`largest`,
  `extreme`, `nearest`, ...) keep every element **tied within the tolerance**, so
  a symmetric part yields a tie instead of an arbitrary winner.
- Scope the snapshot to the body you are building in (`topology.md`).

## Strict cardinality

When the engineering intent is exactly one entity, use `one()`:

| Outcome | Error | Meaning |
|---|---|---|
| Zero matches | `TopologyQueryNoMatchError` (a `NotFoundError`) | The query's assumptions about the model are wrong |
| Several matches | `TopologyQueryAmbiguousError` (a `ConflictError`) | The intent is underspecified — add a criterion |

Both messages list the query steps and the measured facts of the candidates;
read them before refining the query. `first()` is an explicit decision to accept
the first of several — do not use it, or `all()[0]`, to silence ambiguity.

If no combination of facts can identify the intended entity, **stop and report
the SDK gap**. Do not fall back to an index, descriptor parsing or raw COM.

## Re-identification and snapshots

A query holds its snapshot's handles and goes stale with them. After any
geometry-changing operation — feature edit, suppression, direction change, plane
edit, pattern edit, boolean — take a **new** snapshot and run the same query
again. That is how an element is found again, in this process or a fresh one.
It is re-identification by description, not a stored identity.

Within one valid generation, **reuse** a measured snapshot: facts are measured
once per handle, and re-querying an already measured snapshot is cheap, while a
fresh snapshot plus measurement costs on the order of a second on a small part.
Never reuse one across a mutation — `StaleSnapshotError` is the guard.

## Not covered

- Cone, sphere, torus, spline and B-surface facts.
- Outward normals; face or edge adjacency.
- Persistent topology identity across mutations or processes.
- Provenance: which feature *created* an edge.
