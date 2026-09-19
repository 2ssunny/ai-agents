# auto-3dx topology

Edges and faces, how to scope them to a body, and why a snapshot is only good
for a moment. Upstream contract: `docs/api-design.md` section 7.

## Taking a snapshot

```python
edges = part.topology.edges()              # every body in the Part, one flat list
edges = part.topology.edges(body=housing)  # that body only
faces = part.topology.faces(body=housing)

with part.work_in(housing):
    edges = part.topology.edges()          # follows the work body
    edges = part.topology.edges(body=None) # force Part-wide inside a work context
```

**Scope to the body you are building in.** A Part-wide search mixes every body's
topology together, and CATIA will accept a feature built from the wrong body's
edge and only fail at the next rebuild.

## Ownership

Every `Edge` and `Face` carries, read from the model at snapshot time:

| Property | Meaning |
|---|---|
| `owner_body` | The raw body the reference belongs to |
| `owner_body_name` | That body's name |
| `owner_feature_name` | The feature that produced the reference |
| `index` | Position in *this* snapshot — not an identity |
| `descriptor` | CATIA's BRep string, for logging only |

Part Design compares the reference's owner with the body it is building in and
raises `CrossBodyReferenceError` **before** calling CATIA. Treat that as a
targeting mistake: take a snapshot of the right body. Never route around it with
raw COM.

A body's edges include the **wire edges of sketches its features consumed**.
Those are not valid fillet or chamfer inputs — a live fillet attempt on one
failed. Select with `owner_feature_name` after inspecting the model:

```python
solid_edges = [e for e in part.topology.edges(body=housing)
               if e.owner_feature_name == "HOUSING_PAD"]
```

## Staleness

A snapshot is stamped with the Part's model generation. Anything that mutates
the model through any wrapper of that Part invalidates it, including value
writes, closing a `sketch.edit()` block, body visibility changes, **feature
suppression or activation**, and any rebuild whether it succeeded or not. Using a
stale handle raises `StaleSnapshotError` before CATIA is touched.

After `StaleSnapshotError`, take a new snapshot **and re-identify the target**:
the same index in a new snapshot can be a different edge.

## Limits

- **Body-level scoping is supported; feature-level scoping is not.** There is no
  `edges(feature=...)`, and no verified `Topology.Edge,in,<feature>` query. Do
  not invent one.
- **Ownership can be unknown.** When CATIA does not report an owner, the
  cross-body guard allows the call through rather than refusing on a missing
  answer. That is the guard's one hole.
- **The generation registry is process-local.** A new Python process starts
  fresh: an index, a descriptor or an assumption carried over from an earlier
  process means nothing. Take a new snapshot in every process.
- **There is no persistent topology identity.** No selector finds "the top face"
  or "the edge at X". If the SDK cannot prove which edge the user means, say so
  and ask.
- Snapshots restore the user's CATIA selection; `SelectionNotRestoredWarning`
  means only UI selection was lost (safety.md §6).
- Topology search needs the **active** Part, or `InactivePartError`.
