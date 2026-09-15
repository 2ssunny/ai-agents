# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop` (local; ahead of `origin/develop`, unpushed) |
| Last reviewed commit | `6ec542642a5b133781389f0ac7c2d7a024a995d3` |
| Commit date / subject | 2026-09-15 — `feat(inspect): report bodies, geometrical sets and topology counts` |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-15 |
| Unit tests at review | 861 passed (run during review) |
| Live integration at review | Re-run 2026-09-15 after the changes below: 38 passed, 1 skipped (per upstream docs) |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline 6ec542642a5b133781389f0ac7c2d7a024a995d3..HEAD
```

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | Docs and probe only. Live rerun promoted `SketchElement`, shared-generation staleness and the error categories to Verified; export recorded as probed and unavailable |
| `6ec5426` | Topology searches restore the selection (`SelectionNotRestoredWarning`), one generation per CATIA Part across wrappers, and `part.inspect` bodies, geometrical sets and topology counts, all live-tested. Removed the "snapshot changes the selection" and "obtain the Part once" workarounds; inspection promoted to Verified |

## Evidence reviewed

- `docs/api-design.md` (authoritative contract; supersedes the older layering,
  error and root-export sections of `docs/conventions.md`)
- `docs/capabilities.md`, `docs/status.md`, `docs/conventions.md` 1.5, `README.md`
- `src/auto_3dx/__init__.py` root exports and the public classes under
  `core`, `geometry`, `parameters`, `formulas`, `measurement`, `inspect`, `errors`
- `tests/integration/` contents, to decide which public paths the live run covers
  (`test_inspection_live.py`, `test_shared_generation_live.py`,
  `test_edge_features_live.py::test_snapshots_restore_the_user_selection_and_stay_usable`)
- `scripts/probes/` 38 (inspection reads, selection restore) and 39 (export)

## Not yet in the public API

Watch for these on the next sync; promote them only once the SDK implements
them and a live test drives them.

- `part.inspect` for nested geometrical set contents, geometrical sets inside a
  body, and sketches inside a geometrical set (no live read backs them).
- `list`/`get`/`ensure` on planes (`HybridShapes` enumeration is verified).
- File export: probed live and unavailable for PLM-backed documents. Keep it
  unsupported and keep agents away from raw `ExportData`.

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
4. Remove obsolete patterns and workarounds, and add newly retired names to
   `RETIRED_NAMES` in `scripts/validate_skill.py`.
5. Run the validator in the environment where auto-3dx is installed:
   `python skills/global/auto-3dx/scripts/validate_skill.py`. An API check that
   reports SKIPPED has not validated the examples.
6. Search the skill for names the upstream diff removed or renamed.
7. Update the tables above with the new commit, date and evidence state.
8. Review the diff and commit. Do not push unless asked.
