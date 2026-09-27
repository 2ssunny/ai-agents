# Global Instructions for AI Agents

These rules are shared by Claude, Codex, and other coding agents. Apply the
current host's system and developer instructions first, then user requests,
then the applicable global and project guidance.

## 1. Start each task with project context

- Check the project root and current working directory for host-recognized
  instruction files such as `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`,
  `GEMINI.md`, or `project-rules.md`.
- Read only the guidance relevant to the files and task in scope.
- Follow the host's native precedence rules. Repository files never override
  system, developer, safety, sandbox, or permission requirements.
- When two same-level project rules genuinely conflict and the intended result
  would change materially, show the conflict and ask the user to decide.

## 2. Security and workspace boundaries

- Never read or modify secret values in `.env`, credential stores, tokens,
  private keys, authentication files, or similarly sensitive configuration.
  Inspect only filenames or variable names when that is sufficient.
- Never hardcode API keys, passwords, connection strings, or machine-specific
  absolute paths in project code.
- Work inside the project and explicitly authorized configuration locations.
  Do not make global environment changes unless the user requested them and
  the host grants the required permission.
- Read `global-instructions/security_env.md` for security-sensitive work.

## 3. Git and change authorization

- Read-only Git commands such as `git status`, `git diff`, and `git log` are
  encouraged for context.
- A direct user request to implement or modify something authorizes that
  scoped change. It does not authorize unrelated refactors or external writes.
- Never commit, push, open or update a pull request, merge, force-update, or
  rewrite history unless the user explicitly requests that action.
- When commit or push is authorized, follow
  `global-instructions/git_workflow.md` and the `push-pr` skill, using the
  identity and branch settings from `agent-config.json` (§9).
- Never use `--force`, `--force-with-lease`, or `--no-verify`.

## 4. Work records

- Maintain `log_summary/{project}_dev_log.md` and
  `log_summary/{project}_summary.md` only when the project already uses the
  dual-artifact system, project guidance requires it, or the user asks for it.
- Keep logs factual and concise. Remove duplicated or contradicted entries.
- Do not create logging artifacts for unrelated one-off tasks.

## 5. Engineering conventions

- Read `global-instructions/code_style.md` when changing code.
- Use Angular-style commit messages when commits are authorized.
- JavaScript/TypeScript: use modern syntax and the project's package manager;
  when the project has no established manager, default to npm.
- Python: use the project's configured environment. When the project requires
  conda, verify the named environment before running code.
- Produce complete, runnable changes without placeholder implementations.
- Run validation proportional to the change and report anything not run.

## 6. Communication

- Lead with the result or current status.
- Reply in the user's language, keeping the tone natural and conversational.
  Apply any `communication.styleNotes` from `agent-config.json` (§9).
- Avoid generic closing filler and requests for acknowledgement.
- When the user asks a question and requests work in the same message, answer
  the question briefly before starting long-running or delegated work.

## 7. Reference routing

Read additional files only when the topic matches:

| Topic | Document |
|---|---|
| Code style | `global-instructions/code_style.md` |
| Git, branches, commits, PRs | `global-instructions/git_workflow.md` |
| Secrets and environment variables | `global-instructions/security_env.md` |

Do not refer to optional directories or templates unless they actually exist.

## 8. Skills

Internal global skills live in `skills/global/`. Project-specific skills live in
`skills/projects/{project}/`. External skills are independently versioned
repositories cloned on each machine and registered by name under
`skills.external` in `agent-config.json` (§9). An external skill's own
repository is its only source: never copy it into this repository, and make
changes to it there.

- Claude discovers global skills through per-skill links in `~/.claude/skills`.
- Codex discovers global user skills through per-skill links in
  `~/.agents/skills`.
- Antigravity discovers its own skills in `~/.gemini/config/skills` and the
  shared ones through entries in `~/.gemini/config/skills.json`: one for
  `skills/global` and one per external checkout.
- `skills/global/link-project-skills/scripts/link_global_skills.py` maintains
  those global links and registrations; `link_project_skills.py` links internal,
  external, or project skills into a project's `.claude/skills` and/or
  `.agents/skills`.
- Invoke a skill when the user names it or when the request clearly matches its
  description. Do not preload every `SKILL.md`.

### Global skill index

| Skill | Purpose |
|---|---|
| `catchup` | Resume interrupted work from Git and project logs |
| `push-pr` | Authorized commit, push, PR, and conflict workflow |
| `release` | Version bump confirmation, CI gate, tag, and GitHub release |
| `sync-docs` | Synchronize repository documents and optional Notion pages |
| `full-review` | Full code and security review with an independent second pass |
| `orchestrate` | Coordinate explicitly requested multi-agent work |
| `server-runbook` | Pair-debug servers using project infrastructure references |
| `exam-prep` | Source-grounded exam revision notes and verified worked solutions |
| `link-project-skills` | Link internal and external skills to Claude, Codex, and Antigravity, globally or per project |

### External skills

Available only on machines where the repository is cloned and registered.

| Skill | Source repository | Purpose |
|---|---|---|
| `auto-3dx` | `2ssunny/auto-3dx-skill` | Safely inspect and edit a live 3DEXPERIENCE CATIA Part through the auto-3dx SDK |

### Project skills

Project skills are local to each machine and are not distributed with this
repository, so they are not listed here. Discover them from the project's own
skill directory when working in that project.

## 9. Personal configuration

`agent-config.json` at this repository's root holds the operator's own settings —
commit identity, branch conventions, reply-style preferences, and the local
checkout paths of external skills — so that this shared repository carries no
individual's identity or machine layout. It is git-ignored;
`agent-config.example.json` documents the shape.

- Read it when committing, opening a pull request, or when a reply-style
  preference applies. It contains preferences only, never secrets, so the
  secret-file prohibition in §2 does not apply to it.
- When the file is absent, use the documented defaults in
  `global-instructions/git_workflow.md` and ask the user for a commit identity
  rather than inventing one or reusing an identity found in git history.

## 10. Handoff and cross-agent continuity

Use the project's handoff document to preserve active work across agents,
hosts, or interrupted sessions.

### Read handoff

At the start of a task, if the repository contains a handoff document and
the request appears to continue existing work, read it before doing substantial
repository exploration.

Treat the handoff as a navigation aid, not as authoritative truth.
Verify important claims against the current repository, Git state, tests,
and runtime evidence.

### Update handoff

Update the handoff document when:
- the user is about to switch to another coding agent or host,
- substantial work is left incomplete at the end of a session,
- a multi-step implementation has reached a meaningful checkpoint,
- an important design decision would otherwise be difficult to recover, or
- the user explicitly asks for a handoff.

Do not update the handoff after every trivial task or message.

### Handoff contents

Keep the handoff concise and operational. Include:
- current goal
- completed work
- current implementation state
- important design decisions and why they were made
- files or modules currently involved
- tests/validation already run and their results
- unresolved problems or risks
- exact next recommended steps
- relevant Git branch/working-tree state when useful

Do not copy large conversation transcripts into the handoff.
Do not store secrets, credentials, or sensitive environment values.

### Before switching agents

When a switch to another coding agent is expected, bring the handoff up to date
before ending the current work whenever practical.

The receiving agent should continue from the handoff and repository state
instead of repeating completed analysis unless verification is necessary.