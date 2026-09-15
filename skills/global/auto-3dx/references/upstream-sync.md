# Upstream sync record

Maintenance metadata for keeping this skill in step with the auto-3dx SDK.
Agents using the skill do not need this file, and nothing in the skill depends
on a specific commit at runtime.

## Last review

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/2ssunny/auto-3dx` (local clone) |
| Branch reviewed | `develop` (local; 64 commits ahead of `origin/develop`, unpushed) |
| Last reviewed commit | `1d7162fcff152012e969c10fc930240044ef261e` |
| Commit date / subject | 2026-09-15 — `docs: make standard CPython the primary install path and record verified environments` |
| Package version | `0.1.0` (pre-1.0; breaking changes expected) |
| Reviewed on | 2026-09-15 |
| Unit tests at review | 861 passed, run during review in a standard CPython 3.14.2 venv with a regular (non-editable) install, pywin32 312 |
| Live integration at review | 38 passed, 1 skipped in both a standard CPython 3.14.2 venv and a Conda 3.11.16 environment (per upstream docs, 2026-09-15) |

Next sync starts from:

```bash
git -C <auto-3dx-clone> log --oneline 1d7162fcff152012e969c10fc930240044ef261e..HEAD
```

## Review history

| Upstream commit | Outcome |
|---|---|
| `23a0d86` | Initial skill |
| `e32e747` | Docs and probe only. Live rerun promoted `SketchElement`, shared-generation staleness and the error categories to Verified; export recorded as probed and unavailable |
| `6ec5426` | Topology searches restore the selection (`SelectionNotRestoredWarning`), one generation per CATIA Part across wrappers, and `part.inspect` bodies, geometrical sets and topology counts, all live-tested. Removed the "snapshot changes the selection" and "obtain the Part once" workarounds; inspection promoted to Verified |
| `1d7162f` | Packaging, docs, CI and probes only; `src/` unchanged. Standard CPython and Conda both verified live, so the skill gained an environment-neutral interpreter rule, `com3dx` guidance and an environment evidence table. CAD behaviour and safety rules unchanged |

## Python environment evidence

| Environment | Implemented | Unit-tested | Live-tested |
|---|---|---|---|
| Standard CPython venv, editable install | yes | 861 passed (3.14.2) | yes: 38 passed, 1 skipped (3.14.2, pywin32 312) |
| Standard CPython venv, regular install | yes | 861 passed (3.14.2; upstream and this review) | not run |
| Conda environment, editable install | yes | 861 passed (3.11.16) | yes: 38 passed, 1 skipped (3.11.16, pywin32 312) |
| Conda base, `PYTHONPATH=src` | not an install path | 861 passed (3.13.9, pywin32 311) | development runs only |

Packaging basis: `pywin32` is declared only for `sys_platform == "win32"`, the
`test` extra supplies pytest, and `com3dx` is not a dependency. It ships with
3DEXPERIENCE and the transport finds it through `AUTO_3DX_COM3DX_PATH` or the
registered `CATIA.Application` server, which worked from both environments.

Remaining environment limitations:

- Python 3.12 is untested. Upstream added a Windows CPython 3.11–3.14 unit
  workflow, but the branch is unpushed, so no CI result exists yet.
- 32-bit Python, Microsoft Store Python, and 3DEXPERIENCE releases other than
  `B428_Cloud` are unverified.
- A regular (non-editable) install has unit evidence only.
- The first attach from a new interpreter builds its COM wrapper cache.

## Evidence reviewed

- `docs/api-design.md` (authoritative contract; supersedes the older layering,
  error and root-export sections of `docs/conventions.md`)
- `docs/capabilities.md`, `docs/status.md`, `docs/conventions.md` (environment,
  packaging, 1.5), `README.md` (requirements, verified Python environments,
  installation, com3dx discovery)
- `pyproject.toml`, `.github/workflows/unit-tests.yml`,
  `tests/integration/conftest.py`
- `src/auto_3dx/__init__.py` root exports and the public classes under
  `core`, `geometry`, `parameters`, `formulas`, `measurement`, `inspect`, `errors`
- `tests/integration/` contents, to decide which public paths the live run covers
- `scripts/probes/` 01 (com3dx found through the SDK), 38 (inspection reads,
  selection restore) and 39 (export)

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
   the diffs that touch `src/`, `pyproject.toml`, `docs/api-design.md`,
   `docs/capabilities.md`, `docs/status.md`, `README.md`, `tests/integration/`
   and `scripts/probes/`.
2. Ignore internal refactors that leave the public API, safety semantics,
   environment support, and evidence state unchanged.
3. For each agent-visible change, update the smallest part of the skill:
   `SKILL.md` for workflow and safety rules, `references/capabilities.md` for
   capability labels and environment evidence, `references/safety.md` for
   detailed semantics, `references/examples.md` for call shapes. Promote a
   capability or environment to Verified only when a live integration test
   drives it; a class, a mock test, a CI configuration, or a probe of the
   underlying raw reads is not enough.
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
