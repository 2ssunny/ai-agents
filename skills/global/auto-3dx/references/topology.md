# auto-3dx topology

Edges and faces, how to scope them to a body, what ownership means, and why a
snapshot is only good for a moment. Upstream contract: `docs/api-design.md`
section 7. **Selecting** a face or edge is done by measured geometry:
[geometry-query.md](geometry-query.md).

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

## What a handle carries

| Property | Meaning |
|---|---|
| `geometry` | Measured facts — the basis for selection (`geometry-query.md`) |
| `owner_body`, `owner_body_name` | The body the reference belongs to, or `None` when unknown |
| `current_owner_feature_name` | The feature CATIA **currently** reports as the owner |
| `owner_feature_name` | Older alias of the same value; prefer the explicit name |
| `index` | Position in *this* snapshot — diagnostics only, never intent |
| `descriptor` | CATIA's BRep string — logging only, never parsed for selection |

### Current owner is not provenance

`current_owner_feature_name` is the feature CATIA reports as owning the BRep
**now**, which for a solid is the last feature that produced the result. Live,
after a fillet, every edge of the solid — including the untouched ones —
reported the fillet. It does **not** say which feature created an edge; do not
make design-history assumptions from it. Select by geometry, and use
`owned_by(...)` in a query only as a narrowing criterion.

### Unknown body stays unknown

The owning body is read from the model. When CATIA's parent chain does not reach
a body (live, after a session restart, consumed-sketch references returned
generic objects), the SDK looks the feature name up among the bodies and accepts
the answer only if **exactly one** body matches. Otherwise ownership stays
unknown.

`owner_body_name is None` does **not** mean "main body". Never guess ownership.

## Cross-body guard

Part Design compares a reference's owner with the body it is building in and
raises `CrossBodyReferenceError` **before** calling CATIA. Treat it as a
targeting mistake: take a snapshot of the right body. When ownership is unknown,
the guard allows the call through rather than refusing on a missing answer.

A body's edges include the **wire edges of sketches its features consumed**,
which a fillet or chamfer cannot use. Semantic queries on the solid's edges
(`lines()`, `circular()`, position, length) are how to pick a solid edge.

## Staleness

A snapshot is stamped with the Part's model generation. Anything that mutates
the model through any wrapper of that Part invalidates it — value writes,
closing a `sketch.edit()` block, body visibility, feature suppression or
activation, Pad/Pocket direction changes, plane edits, and any rebuild, whether
it succeeded or not. Using a stale handle, or a query built on one, raises
`StaleSnapshotError` before CATIA is touched.

After it, take a new snapshot and **re-run the query**; never reuse the old
index, since the same index can now be a different edge.

## Limits

- **Body-level scoping is supported; feature-level scoping is not.** There is no
  `edges(feature=...)` and no verified `Topology.Edge,in,<feature>` query.
- **The generation registry is process-local.** A fresh process must attach,
  rediscover the model, take a new snapshot and re-run its queries. Never carry
  an index, descriptor or selection across processes.
- **No persistent topology identity.** A query re-identifies an element by
  description on a fresh snapshot; nothing is stored.
- Snapshots restore the user's CATIA selection; `SelectionNotRestoredWarning`
  means only UI selection was lost (safety.md §6).
- Topology search needs the **active** Part, or `InactivePartError`.
