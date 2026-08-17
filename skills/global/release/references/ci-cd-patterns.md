# CI/CD Pipeline Patterns

The default shape for a project's pipeline, and how far to relax it. These
patterns come from production pipelines where each rule was added after the
corresponding failure — the reasoning matters more than the YAML, because the
YAML has to be re-derived for each stack anyway.

## Choosing a tier

Start from **Standard**. Relax to Minimal only when the listed conditions
actually hold; escalate to Full when the project's shape demands it. Say which
tier you chose and why before writing files — an over-built pipeline for a
weekend script wastes the user's time on every push, and an under-built one for
a deployed app fails in front of users.

| | Minimal | **Standard (default)** | Full |
|---|---|---|---|
| Fits | Solo script, library, no deploy target, no external consumers | App with a deploy target or real users | Multi-host, self-hosted runners, or multi-platform artifacts |
| Verify on PR | lint + test + build | same | same, split by install boundary |
| Release | tag → notes only | tag → build, attach artifacts | tag → matrix build, verify, barrier, publish |
| Deploy | manual | push to release branch → deploy + health gate | per-host jobs, health gate, diagnostics, self-heal |
| Artifacts | none | attached to release | verified per platform, draft-then-publish |

Signals to escalate: the project ships installers or binaries; a host has no
public IP; more than one machine must be updated in step; users auto-update from
the release feed.

Signals to relax: nothing consumes the output but the author; deploy is a manual
copy; no build step produces artifacts worth keeping.

## Verify workflow (all tiers)

Runs on pull requests, on GitHub-hosted runners, with no access to servers or
secrets. That isolation is the point — it means a PR from anywhere can be
verified safely.

```yaml
on:
  pull_request:
    branches: [develop, main]

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true    # superseded PR runs are waste
```

- **Split jobs at install boundaries.** A sub-project with its own lockfile is a
  separate job with its own cache key (`cache-dependency-path`), not another step
  in the same job. Sharing one job across two lockfiles silently caches the wrong
  tree.
- **Respect build order.** Shared packages must build before anything that
  typechecks against their output; otherwise the typecheck reads stale or missing
  `dist` files and fails in a way that looks like a type error.
- **Keep infra-dependent tests out.** Unit tests run here; integration tests that
  need a database or a live service run separately. A CI job that needs infra is
  a CI job that is red for reasons unrelated to the change.
- **A `pull_request`-only trigger leaves merge commits unverified.** Add a `push`
  trigger for the release branch when releases are cut from it, or the release
  skill's CI gate has nothing to check. This costs runner minutes on every merge,
  so raise it as a recommendation rather than deciding for the user.

## Release workflow (Standard and up)

Triggered by the version tag, with `permissions: contents: write` and
`fetch-depth: 0`.

**Build and package first, publish as a separate step.** Packaging with
publishing disabled, verifying the output, and only then uploading means a
tag/artifact mismatch can never reach users. When publishing is folded into the
build command, a half-correct build publishes itself before anyone can look at it.

**The tag is the single source of truth for the version.** Validate it is
canonical semver, write it into the manifests and lockfile, then read them back
and confirm the write took. A silent failure here ships an artifact whose
internal version disagrees with its filename, which surfaces much later as an
updater that refuses to update.

**Verify artifacts before uploading.** Check that every expected artifact exists
and that its name and any embedded metadata carry the tag's version. Use
`if-no-files-found: error` on artifact upload so an empty glob fails loudly
instead of producing an empty release.

## Publishing safely (Full tier, and any project with an update feed)

**Put the publish step in a separate job gated on the whole build matrix**
(`needs: build`, `fail-fast: false` in the matrix). GitHub will then not create
or mutate the release unless every platform succeeded. Publishing from inside the
matrix means the first platform to finish publishes a release the others may
never complete.

**Create the release as a draft, upload every asset, then undraft.** A bare
create publishes immediately, opening a window where download pages advertise an
incomplete release and running clients' update checks fail against metadata that
is not uploaded yet.

**Upload order matters when an update feed exists.** Installers first, updater
metadata last — the metadata is what running apps poll and it references the
installers by name and hash. On a re-run against an already-published release
there is no draft window to hide the gap.

**Make re-runs idempotent**: create only when the release does not exist, upload
with `--clobber`, and finish with an undraft that is a no-op when already
published. Releases get re-run more often than anyone expects.

```bash
if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" --verify-tag --title "$TAG" --generate-notes --draft
fi
for artifact in dist/*; do
  case "$(basename "$artifact")" in <metadata-pattern>) continue ;; esac
  gh release upload "$TAG" "$artifact" --clobber
done
for metadata in dist/<metadata-pattern>; do
  gh release upload "$TAG" "$metadata" --clobber
done
gh release edit "$TAG" --draft=false
```

## Deploy workflow (Standard and up)

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch: {}

concurrency:
  group: deploy-${{ github.workflow }}
  cancel-in-progress: false   # never cancel a deploy already in flight
```

The inverted `cancel-in-progress` compared to CI is deliberate: cancelling a
superseded PR check wastes nothing, cancelling a half-applied deploy leaves the
host in an undefined state.

**Self-hosted runners reach hosts that GitHub cannot.** A host behind a VPN with
no public IP can still run a runner that polls GitHub over outbound HTTPS, so no
inbound port has to be opened. This is usually the right answer for private
infrastructure.

**Use a persistent checkout on the host**, not an ephemeral workspace, when the
deploy needs files that live beside the code — environment files, data volumes,
local state. The workflow pulls into that directory; it never touches the secret
files sitting next to it.

**A container being "up" is not a service being ready.** `docker compose up -d`
returns as soon as containers are created, so an immediate health check races the
application's boot and fails on a perfectly healthy deploy. Retry the check for a
bounded window before believing it:

```bash
for i in $(seq 1 30); do
  curl --connect-timeout 3 --max-time 10 -sf "$URL" && break || sleep 2
done
curl --connect-timeout 3 --max-time 10 -sf "$URL"   # final attempt decides
```

**Gate the deploy on health checks.** A deploy that restarts containers and
reports success without confirming the endpoints answer is a deploy that fails
silently.

**Dump diagnostics when a check fails, and make each diagnostic best-effort.**
Under `set -e`, one failing diagnostic command aborts the step and hides every
diagnostic that would have followed — the exact moment the output was needed.
Use `sudo -n` so a missing passwordless grant fails fast instead of hanging on a
password prompt, and `||` on each command so one gap cannot suppress the rest.

**Self-heal only where a specific failure is understood.** Escalating from retry
to a forced recreate is reasonable when that failure mode has been diagnosed and
a plain restart is known not to fix it. Blanket "restart on any failure" logic
converts reproducible bugs into intermittent ones — record why the escalation
exists next to the code that does it.

**Clean up with `if: always()`** so image pruning still runs after a failed
deploy.

## Configuration that changes without editing workflows

Environment-specific URLs and toggles belong in repository variables with an
inline fallback (`${{ vars.API_BASE_URL || 'https://example.com' }}`), not
hardcoded in the workflow. Anything secret belongs in repository secrets and is
referenced, never echoed.

When a step must run on both bash and PowerShell runners, resolve values with
GitHub's `${{ }}` expressions rather than shell variable syntax — `$VAR` and
`$env:VAR` disagree across runner OSes, and a matrix will find that out for you.

## Record what the pipeline deliberately does not do

Unsigned builds, skipped notarization, a manual distribution step, tests that
only run locally — write these in a comment at the top of the workflow with the
user-visible consequence and the condition for revisiting. The next person to
read the file will otherwise assume the gap is a bug and either "fix" it or trip
over it during a release.
