# Release Setup Bootstrap

Run this when the repository has no releases, no tags, or no release automation.
The goal is the smallest setup that makes releases repeatable — resist building
a pipeline the project does not need yet.

## 1. Pick the pipeline tier

Read `ci-cd-patterns.md` and choose a tier — **Standard is the default**, relaxed
to Minimal only when the project genuinely has no deploy target and no external
consumers. State the chosen tier and the reason before creating any file.

| Need | Setup |
|---|---|
| Just a versioned marker with notes | No workflow. `gh release create --generate-notes` is enough |
| Build artifacts attached to the release | Tag-triggered release workflow (§3) |
| Deploy on release | Extend the release workflow, or gate the existing deploy workflow on tags |

Also confirm: which branch releases are cut from (default branch unless told
otherwise), and whether prereleases are expected.

The template in §3 is the Minimal/Standard starting point. For matrix builds,
draft-then-publish ordering, update feeds, and deploy health gates, follow
`ci-cd-patterns.md` rather than growing this template ad hoc.

## 2. Choose the first version

- `v0.1.0` — pre-production; breaking changes still expected without a major bump.
- `v1.0.0` — the public API is something users can now depend on.

Ask rather than assume; the choice communicates stability to whoever consumes
the project. Use a `v` prefix unless the ecosystem says otherwise (Go modules
require it; Python packaging conventionally omits it in the package version
itself, though the git tag may still carry it).

Set the same version in the project manifest so the code and the tag agree.

## 3. Tag-triggered release workflow

`.github/workflows/release.yml` — adjust the build steps to the project's stack:

```yaml
name: Release

on:
  push:
    tags: ['v*.*.*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - run: npm ci
      - run: npm run build

      - name: Publish release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release create "$GITHUB_REF_NAME" --generate-notes
```

Points that matter:

- `permissions: contents: write` is required to create a release; the default
  token is read-only in many repositories.
- `fetch-depth: 0` gives the full history that note generation and any
  changelog tooling need.
- `GITHUB_REF_NAME` is the tag name on a tag push — no parsing required.
- `gh` is preinstalled on GitHub-hosted runners, so no extra action is needed.
- Attach artifacts by appending paths: `gh release create "$GITHUB_REF_NAME" --generate-notes dist/*.zip`.
- When the workflow itself publishes the release, the `release` skill should not
  also run `gh release create` — one or the other, never both.

## 4. Release notes categorization

`.github/release.yml` shapes `--generate-notes` output:

```yaml
changelog:
  exclude:
    labels: [ignore-for-release]
  categories:
    - title: Features
      labels: [feat, enhancement]
    - title: Fixes
      labels: [fix, bug]
    - title: Other Changes
      labels: ['*']
```

**Categorization keys off pull request labels, not commit prefixes.** A project
that uses Angular commit types but never labels its PRs will see everything land
in the catch-all category. Either adopt matching labels (`feat`, `fix`) on PRs,
or skip this file and write notes from the commit log instead — promising
categorized notes that never materialize is worse than plain ones.

## 5. Verify CI covers the release commit

Check how existing workflows are triggered:

```bash
gh workflow list
grep -A3 '^on:' .github/workflows/*.yml
```

A CI workflow triggered only by `pull_request` leaves merge commits on the
default branch with no run of their own, which makes the release gate weaker
than it looks. Adding a `push` trigger for the release branch closes the gap:

```yaml
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [main]
```

Raise this with the user as a recommendation rather than editing their CI
silently — it changes runner usage on every merge.

## 6. Confirm before writing

Show the files to be created and what each does, then create them. Workflow
files are executable configuration in a shared repository; they follow the
normal commit and PR rules, including the `develop` base branch. Do not push
workflow changes straight to the release branch.
