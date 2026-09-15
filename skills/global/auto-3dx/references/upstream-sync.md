# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `main`, pushed. `develop` exists on origin and is merged into `main` |
| Last reviewed commit | `9b2f4023608dc23f4d07b53fce3dfd35093d0649` |
| Commit date / subject | 2026-09-16 — `Merge pull request #3 from 2ssunny/develop` |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-16 |
| Unit tests at review | 868 passed, run during review in a standard CPython 3.14.2 venv (editable install of `HEAD`); GitHub Actions `unit-tests` at `9b2f402` passed on Windows CPython 3.11, 3.12, 3.13 and 3.14 |
| Live integration at review | Standard CPython 3.14.2 venv: 40 passed, including the In-Work Object tests. Conda 3.11.16: 38 passed, 1 skipped, before those tests were added (per upstream docs) |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline 9b2f4023608dc23f4d07b53fce3dfd35093d0649..HEAD
```

**Upstream history was rewritten when it was published.** The commits recorded
below before `9b2f402` are no longer ancestors of `main`. `1d7162f` has the same
tree as `618a75a` on `main`, so this review compared trees with
`git diff 1d7162f HEAD`. If a recorded commit is ever missing from the ancestry
again, compare trees the same way instead of reading `log <old>..HEAD`.

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | Docs and probe only. Live rerun promoted `SketchElement`, shared-generation staleness and the error categories to Verified; export recorded as probed and unavailable |
| `6ec5426` | Topology searches restore the selection (`SelectionNotRestoredWarning`), one generation per CATIA Part across wrappers, and `part.inspect` bodies, geometrical sets and topology counts, all live-tested. Removed the "snapshot changes the selection" and "obtain the Part once" workarounds; inspection promoted to Verified |
| `1d7162f` | Packaging, docs, CI and probes only; `src/` unchanged. Standard CPython and Conda both verified live, so the skill gained an environment-neutral interpreter rule, `com3dx` guidance and an environment evidence table. CAD behaviour and safety rules unchanged |
| `9b2f402` | Published on `main` with rewritten history. `part.inspect.in_work_object()` / `summary.in_work_object` added and live-tested on standard CPython; CI verified the unit suite on Windows CPython 3.11–3.14; upstream fixed the three recorded doc drifts |

## Python environment evidence

| Environment | Implemented | Unit-tested | Live-tested |
|---|---|---|---|
| Standard CPython venv, editable install | yes | 868 passed (3.14.2; upstream and this review) | yes: 40 passed (3.14.2, pywin32 312) |
| Standard CPython venv, regular install | yes | 868 passed (3.14.2) | not run |
| Conda environment, editable install | yes | 868 passed (3.11.16) | yes: 38 passed, 1 skipped (3.11.16, pywin32 312), before the In-Work Object tests |
| Conda base, `PYTHONPATH=src` | not an install path | 868 passed (3.13.9, pywin32 311) | development runs only |
| GitHub Actions Windows runner, regular install | yes | passed on 3.11, 3.12, 3.13, 3.14 at `9b2f402` | none (no 3DEXPERIENCE) |

Packaging basis: `pywin32` is declared only for `sys_platform == "win32"`, the
`test` extra supplies pytest, and `com3dx` is not a dependency. It ships with
3DEXPERIENCE and the transport finds it through `AUTO_3DX_COM3DX_PATH` or the
registered `CATIA.Application` server, which worked from both live environments.

Remaining environment limitations:

- Live integration has run only on CPython 3.14.2 and Conda 3.11.16. Python 3.12
  and 3.13 have unit evidence only.
- The In-Work Object live tests have run on standard CPython 3.14.2 only.
- 32-bit Python, Microsoft Store Python, and 3DEXPERIENCE releases other than
  `B428_Cloud` are unverified.
- A regular (non-editable) install has unit evidence only.
- The first attach from a new interpreter builds its COM wrapper cache.

## Evidence reviewed

- `docs/api-design.md` (authoritative contract; supersedes the older layering,
  error and root-export sections of `docs/conventions.md`), including section 11
  on the In-Work Object
- `docs/capabilities.md`, `docs/status.md`, `docs/conventions.md` (environment,
  packaging, 1.5 including the In-Work Object measurements), `README.md`
  (verified Python environments, model inspection)
- `pyproject.toml`, `.github/workflows/unit-tests.yml` and its run at `9b2f402`
  (per-job results), `tests/integration/conftest.py`
- `src/auto_3dx/__init__.py` root exports and the public classes under
  `core`, `geometry`, `parameters`, `formulas`, `measurement`, `inspect`, `errors`
- `tests/integration/` contents, to decide which public paths the live run covers
  (`test_inspection_live.py::test_in_work_object_follows_temporary_geometry_and_cleanup`)
- `scripts/probes/` 01 (com3dx found through the SDK), 38 (inspection reads,
  selection restore) and 39 (export)

## Not yet in the public API

Watch for these on the next sync; promote them only once the SDK implements
them and a live test drives them.

- `part.inspect` for nested geometrical set contents, geometrical sets inside a
  body, and sketches inside a geometrical set (no live read backs them).
- Setting the In-Work Object (read-only today; no public setter).
- `list`/`get`/`ensure` on planes (`HybridShapes` enumeration is verified).
- File export: probed live and unavailable for PLM-backed documents. Keep it
  unsupported and keep agents away from raw `ExportData`.

## Upstream documentation drift seen at this review

None open. The three drifts recorded at earlier reviews (constraint arguments
in `docs/capabilities.md` 3.4.1, Rib and Slot arguments in `README.md`, and the
`snapshot_edges()` references in docstrings) were fixed upstream.

## Sync procedure

1. `git status` and `git log <last-reviewed>..HEAD` in the auto-3dx clone. If the
   last reviewed commit is not an ancestor of `HEAD`, compare trees with
   `git diff <last-reviewed> HEAD`. Read the diffs that touch `src/`,
   `pyproject.toml`, `docs/api-design.md`, `docs/capabilities.md`,
   `docs/status.md`, `README.md`, `tests/integration/` and `scripts/probes/`.
2. Ignore internal refactors that leave the public API, safety semantics,
   environment support, and evidence state unchanged.
3. For each agent-visible change, update the smallest part of the skill:
   `SKILL.md` for workflow and safety rules, `references/capabilities.md` for
   capability labels and environment evidence, `references/safety.md` for
   detailed semantics, `references/examples.md` for call shapes. Promote a
   capability or environment to Verified only when a live integration test
   drives it; a class, a mock test, a CI configuration, or a probe of the
   underlying raw reads is not enough. A completed CI run is unit evidence only.
4. Remove obsolete patterns and workarounds, and add newly retired names to
   `RETIRED_NAMES` in `scripts/validate_skill.py`.
5. Run the validator with the interpreter whose auto-3dx installation should be
   checked (venv, Conda or other):
   `python skills/global/auto-3dx/scripts/validate_skill.py`. It prints the
   interpreter and `auto_3dx` it used. An API check that reports SKIPPED has not
   validated the examples.
6. Search the skill for names the upstream diff removed or renamed, and for
   machine-specific interpreter paths or environment names.
7. Update the tables above with the new commit, date and evidence state.
8. Review the diff and commit. Do not push unless asked.
