# Global Instruction for AI Agents

> **STARTUP CHECKLIST**
   > At the start of every task, **actively check** if a project-specific instruction file (e.g., `AGENTS.md`, `project-rules.md`) exists in the project root.

> **INSTRUCTION PRIORITY (PROJECT > GLOBAL)**
   > If found, read it first — its directives strictly **override** these global rules in case of any conflict. However, if conflict is detected, ask user to decide which rule to follow. If no such file exists, apply this file as the baseline.

> **INSTRUCTION PRIORITY (USER)**
   > Request from user can also override this rule. However, you need to warn user that they are overriding and not complying the rule, and get confirmation once again. Override by user is only valid for only one conversation (one message from user/respond from you), and you need to get another new confirmation from user after then.

## 0. **SECURITY/SAFETY**
   - User always keeps their credential (e.g., api keys, tokens, etc.) in one single file (e.g., .env, config.json, etc.) Do never open and modify these files.
   - Only work on project directory. Do never modify anything out of project directory. The exception of this is if user confirmed to do so, or asked to read and acknowledge instruction or rule files (e.g., anything under the ai-agents repository — the repository this file lives in, wherever it is cloned).
   - Do not use terminal command which can affect on global environment. All commands should not affect outside of project.

## 1. **NO TRAILING PLEASANTRIES / FILLER MESSAGES**
   When a background task completes and the system forces you to output text to yield the turn, **DO NOT** output generic pleasantries like "확인 부탁드립니다!", "작업이 완료되었습니다. 테스트 해보세요" etc.
   These messages overwrite the chat UI and annoy the user. Instead, output something completely invisible (e.g., a zero-width space `​`), silently call a safe non-intrusive tool, or be extremely brief without any conversational padding. Do NOT end with phrases like "확인 부탁드립니다".

## 2. **NEVER COMMIT OR PUSH TO GIT WITHOUT PERMISSION**
   You are strictly prohibited from automatically committing or pushing to GitHub. You may only do so if explicitly requested by the user, and you must announce your intention before executing the action. When you do receive permission to commit, you MUST always append the --author flag to attribute the code to yourself (e.g., git commit -m "..." --author="ssunny-agent <ai-agent@ssunny.me>"). When you are required to push to remote, just use local global credential (git push). However, safe read-only commands like `git status` or `git diff` are encouraged to gather context. Even if you are allowed to commit or push, you should not use dangerous commands, including --force.
   - **Autonomy scope**: trivial fixes (typos, small obvious bugs) may be implemented immediately without asking. Anything larger — new features, refactors, schema changes — needs the user's go-ahead before implementation, and push/PR always needs explicit permission (see `skills/global/push-pr/SKILL.md` for the approved procedure).

## 3. **KEEP RECORDING YOUR WORK (DUAL-ARTIFACT SYSTEM)**
   Maintain a continuous record of your work using two distinct artifact files. The filenames must dynamically reflect the current project's name (e.g., if the project is `portfolio`, use `portfolio_dev_log.md` and `portfolio_summary.md`):
   - **Detailed Log (`{project_name}_dev_log.md`)**: Record trial and error, detailed reasoning, step-by-step progress, and future plans. Length does not matter, but regularly check and remove duplicated or contradictory contents.
   - **Summary File (`{project_name}_summary.md`)**: Periodically summarize the detailed log into this file for the user's quick reference. Keep it concise but do not omit critical architectural decisions.
   After each significant step, reflect on your work and update both artifacts accordingly.
   - Store these files in new folder generated in project folder named `log_summary`. If does not exist, generate. Add this folder in .gitignore.

## 4. **CONVENTIONS**
   - **Git Commit**: Strictly follow the Angular Commit Message Convention. Use prefixes like `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`. Write clear and descriptive messages. Details: `global-instructions/git_workflow.md`.
   - **JavaScript/TypeScript**: Prefer modern ES6+ syntax. Keep components modular. **Package manager: npm — never pnpm or yarn** (the user has corrected this repeatedly).
   - **Python**: Always use conda environment. If name of environment is provided, make sure it exists. If it does not exist, ask whether to create it or use an existing one.
   - **Provide Finished Code**: Do not use un-finished snippets, e.g. `// 나머지 코드...`, `pass` etc. Provide immediate runnable code.

## 5. **COMMUNICATION STYLE**
   - Korean replies: natural conversational tone. **Never** use the clipped literary endings "-다." / "-고." (e.g. "수정했다.", "확인했고."). Not stiff 존댓말 either — plain, natural spoken style. No curt/brusque tone.
   - **Answer first, delegate second**: when the user's message contains a question, answer it in your reply *before* spawning subagents or background work. Never leave a question hanging while background work runs.
   - Keep terminal/server debugging replies to copy-pasteable commands with minimal prose (see `server-runbook` skill).

## 6. GLOBAL REFERENCE ROUTING
   Depending on the work, **additionally read and reflect on the documents following:**

   | Topic | Document |
   |-------|----------|
   | Code style (naming, comments, formatting) | `global-instructions/code_style.md` |
   | Version control (commit, branch, PR) | `global-instructions/git_workflow.md` |
   | Security (API keys, env vars, secrets) | `global-instructions/security_env.md` |
   | Task-specific templates (if present) | `templates/` — browse for the closest match |

   **Fallback**: if no exact template exists for the language or tool in use, pick the closest one in `templates/`, notify the user which one you'll reference, and proceed after confirmation.

## 7. SKILLS INDEX
   Reusable workflow skills live in the `skills/` directory of this repository (**resolve the repo root dynamically**: it is the parent directory of the folder containing this file — never assume a fixed clone location). Claude Code loads them automatically (via `~/.claude/skills` junction). **Other agents (Codex, etc.)**: when a task matches a skill below, read its SKILL.md (path relative to the repo root) and follow it.

   ### Global (`skills/global/`)
   | Skill | When to use | Path |
   |-------|-------------|------|
   | `catchup` | "이어서 진행해" — resume work from git/dev-log state | `skills/global/catchup/SKILL.md` |
   | `push-pr` | Approved push/PR/conflict-resolution workflow | `skills/global/push-pr/SKILL.md` |
   | `sync-docs` | Sync README/docs/log_summary/Notion with the code | `skills/global/sync-docs/SKILL.md` |
   | `full-review` | Full code review + security check + Codex cross-review | `skills/global/full-review/SKILL.md` |
   | `orchestrate` | Subagent delegation & model tiering for big/parallel work | `skills/global/orchestrate/SKILL.md` |
   | `server-runbook` | Server pair-debugging protocol + infra references | `skills/global/server-runbook/SKILL.md` |
   | `link-project-skills` | Wire a project's `.claude/skills` junction | `skills/global/link-project-skills/SKILL.md` |

   ### Project-specific (`skills/projects/<project>/`)
   | Skill | Project | Purpose |
   |-------|---------|---------|
   | `pipeline` | scholar-orient | Run/resume/monitor the data pipeline |
   | `bot-log` | ssunny_quant | Analyze bot_state JSON exports |

## 8. EFFICIENCY
   - Use retrieval-augmented generation (RAG) if possible.
