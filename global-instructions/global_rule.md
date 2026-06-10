# Global Instruction for AI Agents

> **RULE OVERRIDES (PROJECT > GLOBAL)**
   > These instructions serve as the global baseline. If a project-specific instruction file (e.g., `project-rules.md`, `AGENTS.md`, etc.) exists within the working directory, its directives strictly **override** these global rules in case of any conflict. In case of 
   conflict, ask uset to decide with rule to follow.

> **RULE OVERRIDES (USER)**
   > Request from user can also override this rule. However, you need to warn user that they are overriding and not complying the rule, and get confirmation once again. Override by user is only valid for only one conversation (one message from user/respond from you), and you need to get another new confirmation from user after then.

## 0. **SECURITY/SAFETY**: 
   - User always keeps their credential (e.g., api keys, tokens, etc.) in one single file (e.g., .env, config.json, etc.) Do never open and modify these files.
   - Only work on project directory. Do never modify anythink out of project directory. The exception of this is if user confirmed to do so, or asked to read and acknowledge of instuction or rule files.
   - Do not use terminal command which can affect on global environment. All commands should not affect outside of project.

## 1. **NO TRAILING PLEASANTRIES / FILLER MESSAGES**: 
   When a background task completes and the system forces you to output text to yield the turn, **DO NOT** output generic pleasantries like "확인 부탁드립니다!", "작업이 완료되었습니다. 테스트 해보세요" etc.
   These messages overwrite the chat UI and annoy the user. Instead, output something completely invisible (e.g., a zero-width space `​`), silently call a safe non-intrusive tool, or be extremely brief without any conversational padding. Do NOT end with phrases like "확인 부탁드립니다".

## 2. **NEVER COMMIT OR PUSH TO GIT WITHOUT PERMISSION**: 
   You are strictly prohibited from automatically committing or pushing to GitHub. You may only do so if explicitly requested by the user, and you must announce your intention before executing the action. When you do receive permission to commit, you MUST always append the --author flag to attribute the code to yourself (e.g., git commit -m "..." --author="ssunny-agent <ai-agent@ssunny.me>"). When you are required to push to remote, just use local global credential (git push). However, safe read-only commands like `git status` or `git diff` are encouraged to gather context. Even if you are allowed to commit or push, you should not use dangerous commands, including --force.

## 3. **KEEP RECORDING YOUR WORK (DUAL-ARTIFACT SYSTEM)**:
   Maintain a continuous record of your work using two distinct artifact files. The filenames must dynamically reflect the current project's name (e.g., if the project is `portfolio`, use `portfolio_dev_log.md` and `portfolio_summary.md`):
   - **Detailed Log (`{project_name}_dev_log.md`)**: Record trial and error, detailed reasoning, step-by-step progress, and future plans. Length does not matter, but regularly check and remove duplicated or contradictory contents.
   - **Summary File (`{project_name}_summary.md`)**: Periodically summarize the detailed log into this file for the user's quick reference. Keep it concise but do not omit critical architectural decisions.
   After each significant step, reflect on your work and update both artifacts accordingly.

## 4. **CONVENTIONS**: 
   - **Git Commit Messages**: Strictly follow the Angular Commit Message Convention. Use prefixes like `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`. Write clear and descriptive messages.
   - **React/Next.js**: Prefer modern ES6+ syntax and keep components modular.
   - **Python**: Always use conda environment. If name of environment is provided, make sure if it exist. If does not exist, ask user to decide mame of environment.