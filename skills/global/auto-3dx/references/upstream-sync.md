# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop` (local; ahead of `origin/develop`, unpushed) |
| Last reviewed commit | `e32e7472001250379102c6125a8499e7e9af41d5` |
| Commit date / subject | 2026-09-15 — `docs: stop claiming HybridShapes enumeration is unverified` |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-15 |
| Unit tests at review | 832 passed (run at `23a0d86`; `src/` and `tests/` unchanged since) |
| Live integration at review | Re-run 2026-09-15 after the refactor: 34 passed, 1 skipped (per upstream docs) |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline e32e7472001250379102c6125a8499e7e9af41d5..HEAD
```

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | Docs and probe only. Live rerun promoted `SketchElement`, shared-generation staleness and the error categories to Verified; export recorded as probed and unavailable |

## Evidence reviewed

- `docs/api-design.md` (authoritative contract; supersedes the older layering,
  error and root-export sections of `docs/conventions.md`)
- `docs/capabilities.md`, `docs/status.md`, `docs/conventions.md` 1.5, `README.md`
- `src/auto_3dx/__init__.py` root exports and the public classes under
  `core`, `geometry`, `parameters`, `formulas`, `measurement`, `inspect`, `errors`
- `tests/integration/` contents, to decide which public paths the live run covers
- `scripts/probes/` 38 (inspection reads, selection restore) and 39 (export)

## Live-verified upstream but not yet in the public API

Watch for these on the next sync; promote them only once the SDK implements them.

- Topology snapshots restoring the user's selection (restore verified by probe 38).
  Until implemented, the skill keeps saying a snapshot changes the selection.
- One generation per CATIA Part across `Part` wrappers (Part COM identity verified).
  Until implemented, the skill keeps "obtain the Part once".
- `part.inspect` fields for other bodies, geometrical sets, and edge and face counts
  (reads verified by probe 38).
- `HybridShapes` enumeration (verified); no `list`/`get`/`ensure` on planes yet.

## Upstream documentation drift seen at this review

Recorded so the next sync does not mistake these for API changes. The code
was followed in each case.

- `docs/capabilities.md` 3.4.1 still says constraint methods take raw COM
  objects; since `8ee1f33` they take the `SketchElement` the editor returns.
- `README.md` says Rib and Slot take raw COM sketches; the signatures take
  `Sketch` wrappers.
- `create_edge_fillet` and `create_chamfer` docstrings still point at the
  deprecated `snapshot_edges()`.

## Sync procedure

1. `git status` and `git log <last-reviewed>..HEAD` in the auto-3dx clone; read
   the diffs that touch `src/`, `docs/api-design.md`, `docs/capabilities.md`,
   `docs/status.md`, `tests/integration/` and `scripts/probes/`.
2. Ignore internal refactors that leave the public API, safety semantics, and
   evidence state unchanged.
3. For each agent-visible change, update the smallest part of the skill:
   `SKILL.md` for workflow and safety rules, `references/capabilities.md` for
   capability labels, `references/safety.md` for detailed semantics,
   `references/examples.md` for call shapes. Promote a capability to Verified
   only when a live integration test drives that public path; a class, a mock
   test, or a probe of the underlying raw reads is not enough.
4. Remove obsolete patterns, and add newly retired names to `RETIRED_NAMES` in
   `scripts/validate_skill.py`.
5. Run the validator in the environment where auto-3dx is installed:
   `python skills/global/auto-3dx/scripts/validate_skill.py`. An API check that
   reports SKIPPED has not validated the examples.
6. Search the skill for names the upstream diff removed or renamed.
7. Update the tables above with the new commit, date and evidence state.
8. Review the diff and commit. Do not push unless asked.
