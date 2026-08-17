---
name: release
description: Publish a versioned GitHub release — read the latest version, confirm the semantic bump level with the user, verify CI passed on the exact commit being released, then tag and publish. Also covers designing or repairing the CI/CD pipeline itself. Use when the user asks to cut a release, publish or tag a version, bump a version number, set up release or deployment automation, add GitHub Actions workflows, or diagnose a failed CI, release, or deploy run.
---

# Release

A release is public and awkward to retract, and a tag on untested code is the
failure this workflow exists to prevent. So two gates are non-negotiable: the
**user chooses the version level**, and **CI must be green on the exact commit**
being tagged. Everything else is mechanics.

Two neighbouring tasks route elsewhere:

- Repository has no release setup at all → `references/setup.md` (bootstrap).
- Building, repairing, or reviewing the pipeline itself (CI, deploy, artifact
  publishing) → `references/ci-cd-patterns.md`, which holds the default pipeline
  shape and when to relax it.

## 1. Establish the current state

Verify `gh auth status` first; every step below depends on it.

```bash
gh release list --limit 5
git fetch --tags --prune && git tag --sort=-v:refname | head -5
```

Three sources can disagree — published releases, raw tags, and the version
field in the project manifest (`package.json`, `pyproject.toml`, `Cargo.toml`,
`VERSION`). Read all that exist. When they disagree, report the discrepancy and
ask which is authoritative rather than picking one; a wrong baseline produces a
version number that collides or skips.

Note the existing **tag format** (`v1.2.3` vs `1.2.3`) and reuse it exactly.
Mixed formats in one repository break tooling that sorts or matches tags.

When no release or tag exists yet, this is a first release: go to
`references/setup.md`.

## 2. Propose the bump, then wait for the user

Summarize what is being released before asking:

```bash
git log <last-tag>..HEAD --oneline --no-merges
```

Map the work to a recommendation — breaking changes mean major, `feat:` commits
mean minor, and only `fix:`/`chore:` means patch. Present the concrete resulting
versions so the choice is about the release, not about semver theory:

> 마지막 릴리스 v1.3.2 이후 feat 3개, fix 5개. breaking change는 없어 보여요.
> - minor → **v1.4.0** (권장)
> - patch → v1.3.3
> - major → v2.0.0

Ask about prerelease (`-rc.1`, `-beta.1`) only when the commits or the user's
framing suggest it. **Stop here and wait.** Choosing the level unilaterally
defeats the purpose of the skill even when the answer looks obvious.

## 3. Pre-flight the release commit

Releases are cut from the default branch (usually a protected branch such as
`main`, per `agent-config.json`) after the user has merged there — never push
commits to a protected branch just to make a release possible.

- Working tree clean; if not, stop and resolve that first.
- On the release branch and synced: `git fetch && git status -sb` shows no
  divergence from the remote.
- Record the target SHA: `git rev-parse HEAD`. Every later step refers to this
  exact commit.
- Confirm the tag is unused: `git tag -l <tag>` and `gh release view <tag>`.

## 4. Gate on CI

Check the target commit, not the branch:

```bash
gh run list --commit <sha> --limit 10
```

| Result | Action |
|---|---|
| All completed successfully | Proceed |
| Any run in progress | `gh run watch <run-id>`; report progress, then re-evaluate |
| Any run failed | **Stop.** `gh run view <run-id> --log-failed`, report the failing job and cause. Do not tag |
| No runs found | See below — do not assume green |

"No runs found" is common and must not be silently treated as a pass. Workflows
triggered only by `pull_request` never run against the merge commit on the
default branch; the checks executed against the PR head instead. Recover the
association:

```bash
gh api repos/{owner}/{repo}/commits/<sha>/pulls --jq '.[].number'
gh pr checks <number>
```

Then say plainly what was verified — "CI는 PR #42의 head 커밋에서 통과했고, main
머지 커밋 자체에는 실행 이력이 없어요" — and let the user decide. If nothing
verified the code at all, recommend running CI on the branch before tagging
rather than releasing blind.

## 5. Bump the version in the project files

Only when the project stores its version in a file. Update every manifest that
carries it (and its lockfile, when the tool writes one), then commit:

```
chore(release): v1.4.0
```

Follow the `push-pr` skill's rules for the commit — author signature, no
co-author lines. The version commit must land on the remote *before* tagging so
the tag points at a commit that already declares its own version; otherwise the
released source says one version and the tag says another. Re-record the SHA
after this commit and re-check CI on it (step 4) — it is a new commit.

## 6. Tag and publish

Annotated tags carry the tagger and message that GitHub displays; lightweight
tags do not.

```bash
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin v1.4.0
gh release create v1.4.0 --generate-notes --title "v1.4.0"
```

- `--generate-notes` builds notes from merged PRs, shaped by `.github/release.yml`
  when present.
- Add `--prerelease` for rc/beta tags, `--draft` when the user wants to review
  the notes before they go public, `--target <sha>` when the tag must pin a
  commit other than the branch head.
- Attach build artifacts by listing them after the tag when the release ships
  binaries and no workflow does it.

Publishing is outward-facing: confirm the final tag, title, and prerelease flag
with the user before running the create command unless they already approved
these specifics.

## 7. Follow the release workflow through

A tag push usually triggers build/deploy automation, and the release is not
actually done until that finishes:

```bash
gh run list --workflow release.yml --limit 3
gh run watch <run-id>
```

If it fails, the tag and release exist while the artifacts do not — say so
explicitly rather than reporting success. Recovery depends on the cause: re-run
the workflow for infrastructure flakes, or delete both the release and the tag
(`gh release delete <tag> --cleanup-tag`) and redo after fixing a real defect.
Deleting a published release is destructive, so confirm before doing it.

## Report

Version released, the commit it points at, how CI was verified, the release URL,
and the state of any triggered workflow. Mention anything skipped or unverified —
an unverified release the user believes was gated is worse than a delayed one.
