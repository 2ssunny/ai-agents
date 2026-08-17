# Global Instructions for AI Agents

These rules are shared by Claude, Codex, and other coding agents. Apply the
current host's system and developer instructions first, then user requests,
then the applicable global and project guidance.

## 1. Start each task with project context

- Check the project root and current working directory for host-recognized
  instruction files such as `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`, or
  `project-rules.md`.
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

Global skills live in `skills/global/`. Project-specific skills live in
`skills/projects/{project}/`.

- Claude discovers global skills through `~/.claude/skills`.
- Codex discovers global user skills through `~/.agents/skills`.
- Projects may expose project skills through `.claude/skills` and/or
  `.agents/skills` junctions.
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
| `link-project-skills` | Connect centralized project skills to Claude and/or Codex |

### Project skills

Project skills are local to each machine and are not distributed with this
repository, so they are not listed here. Discover them from the project's own
skill directory when working in that project.

## 9. Personal configuration

`agent-config.json` at this repository's root holds the operator's own settings —
commit identity, branch conventions, and reply-style preferences — so that this
shared repository carries no individual's identity. It is git-ignored;
`agent-config.example.json` documents the shape.

- Read it when committing, opening a pull request, or when a reply-style
  preference applies. It contains preferences only, never secrets, so the
  secret-file prohibition in §2 does not apply to it.
- When the file is absent, use the documented defaults in
  `global-instructions/git_workflow.md` and ask the user for a commit identity
  rather than inventing one or reusing an identity found in git history.
