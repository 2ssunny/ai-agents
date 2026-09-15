# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop` (local; ahead of `origin/develop`, unpushed) |
| Last reviewed commit | `23a0d86aad8eb75dd89baa88bafc266fedab3b33` |
| Commit date / subject | 2026-09-15 — `docs: describe SketchElement in the user docs` |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-15 |
| Unit tests at review | 832 passed (run during review) |
| Live integration at review | Last run predates the 2026-09-14 refactor (34 passed, 1 skipped, per upstream docs); not re-run since |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline 23a0d86aad8eb75dd89baa88bafc266fedab3b33..HEAD
```

## Evidence reviewed

- `docs/api-design.md` (authoritative contract; supersedes the older layering,
  error and root-export sections of `docs/conventions.md`)
- `docs/capabilities.md`, `docs/status.md`, `README.md`
- `src/auto_3dx/__init__.py` root exports and the public classes under
  `core`, `geometry`, `parameters`, `formulas`, `measurement`, `inspect`, `errors`
- `tests/integration/` file list, `scripts/probes/` list (38 inspection and 39
  export exist as probes only, not run live)

## Upstream documentation drift seen at this review

Recorded so the next sync does not mistake these for API changes. The code
was followed in each case.

- `docs/capabilities.md` 3.4.1 still says constraint methods take raw COM
  objects; since `8ee1f33` they take the `SketchElement` the editor returns.
- `README.md` says Rib and Slot take raw COM sketches; the signatures take
  `Sketch` wrappers.
- `create_edge_fillet` docstring still points at the deprecated
  `snapshot_edges()`.
- Upstream docs state 811 unit tests; 832 pass at this commit.

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
   only with live evidence; a class or a mock test is not enough.
4. Remove obsolete patterns, and add newly retired names to `RETIRED_NAMES` in
   `scripts/validate_skill.py`.
5. Run the validator in the environment where auto-3dx is installed:
   `python skills/global/auto-3dx/scripts/validate_skill.py`. An API check that
   reports SKIPPED has not validated the examples.
6. Search the skill for names the upstream diff removed or renamed.
7. Update the table above with the new commit, date and evidence state.
8. Review the diff and commit. Do not push unless asked.
