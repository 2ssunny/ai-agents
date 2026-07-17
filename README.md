# AI-AGENTS — 에이전트 공용 지침 & 스킬 저장소

모든 AI 코딩 에이전트(Claude Code, Codex 등)가 공유하는 규칙과 재사용 워크플로우(스킬)의 단일 원본(single source of truth). 각 에이전트는 얇은 어댑터(정션/포인터)로만 연결되고, 내용은 전부 이 저장소에서 관리한다.

## 구조

```
ai-agents/
├── global-instructions/
│   ├── global_rule.md        ← 진입점(Router). 모든 에이전트가 가장 먼저 읽음
│   ├── code_style.md         ← 코드 스타일 기준
│   ├── git_workflow.md       ← 커밋/브랜치/PR 전략 (develop 기반, --author 서명)
│   └── security_env.md       ← 시크릿/환경변수 규칙
├── skills/
│   ├── global/               ← 전역 스킬 (모든 프로젝트에서 사용)
│   │   ├── catchup/              작업 재개 ("이어서 진행해")
│   │   ├── push-pr/              승인된 push/PR 워크플로우
│   │   ├── sync-docs/            문서·노션 동기화
│   │   ├── full-review/          전체 코드리뷰 + codex 교차 리뷰
│   │   ├── orchestrate/          서브에이전트·모델 티어링 정책
│   │   ├── server-runbook/       서버 페어 디버깅 (+ references/)
│   │   └── link-project-skills/  프로젝트 스킬 정션 자동 설정
│   └── projects/             ← 프로젝트 특화 스킬 (해당 프로젝트에서만 노출)
│       ├── scholar-orient/pipeline/   데이터 파이프라인 운영
│       └── ssunny-quant/bot-log/      트레이딩 봇 로그 분석
├── templates/                ← 작업 유형별 구현 가이드 (필요 시 추가)
├── human-rules/
│   └── general_rule.md       ← 인간 검토용 체크리스트
└── ai_agents_blueprint.md    ← 시스템 설계 문서
```

## 에이전트별 배선(wiring)

내용 복사 없이 포인터만 연결한다. 원본 수정은 모든 에이전트에 즉시 반영된다.

> **경로 원칙**: 이 저장소는 어디에 clone해도 된다. 저장소 안의 문서·스킬에는 절대경로를 쓰지 않는다 — 절대경로는 각 머신의 어댑터(아래 정션과 포인터 파일)에만 존재한다. 아래에서 `<ai-agents-root>`는 자신의 clone 위치로 치환.

### Claude Code

| 연결 | 방법 |
|------|------|
| 전역 규칙 자동 로드 | `~/.claude/CLAUDE.md`에 3줄 포인터 → `<ai-agents-root>\global-instructions\global_rule.md` |
| 전역 스킬 | 정션: `cmd /c mklink /J "%USERPROFILE%\.claude\skills" "<ai-agents-root>\skills\global"` |
| 프로젝트 특화 스킬 | 정션: `<프로젝트>\.claude\skills` → `<ai-agents-root>\skills\projects\<프로젝트>` |

`~/.claude/CLAUDE.md` 포인터 내용 (경로만 자신의 clone 위치로):

```markdown
# Global rules

At the start of every session, read `<ai-agents-root>\global-instructions\global_rule.md`
and comply with it for the whole session. It routes to code style, git workflow,
security rules, and the skills index.
```

새 프로젝트에 특화 스킬을 연결하려면 그 프로젝트에서 `link-project-skills` 스킬을 실행하면 된다 (정션 생성 + .gitignore 처리 자동).

정션 생성 직후에는 **새 세션부터** 스킬 목록에 반영된다. 이후 ai-agents 쪽 수정은 즉시 반영.

### Codex

`~/.codex/AGENTS.md`에 동일한 3줄 포인터를 넣는다 (경로는 자신의 clone 위치로):

```markdown
At the start of every session, read `<ai-agents-root>\global-instructions\global_rule.md`
and comply with it. It routes to code style, git workflow, security rules, and the skills index.
```

스킬은 `global_rule.md`의 **SKILLS INDEX** 섹션이 라우팅한다 — 작업이 스킬에 해당하면 해당 SKILL.md를 읽고 따르게 되어 있다. (스킬 파일은 표준 markdown이라 어떤 에이전트든 읽을 수 있음)

### 기타 에이전트 (Antigravity 등)

자체 rules 파일에 같은 3줄 포인터를 넣으면 동일하게 동작한다.

## 스킬 추가/수정

- 전역 스킬: `skills/global/<이름>/SKILL.md` 생성 → `global_rule.md`의 SKILLS INDEX에 한 줄 추가.
- 프로젝트 스킬: `skills/projects/<프로젝트>/<이름>/SKILL.md` 생성 (정션이 이미 있으면 그걸로 끝).
- 형식: YAML frontmatter(`name`, `description`) + 본문. description이 트리거 조건을 결정하므로 "언제 쓰는지"를 구체적으로 적을 것. 긴 참고자료는 `references/`로 분리.

## 설계 원칙

1. **Single Source of Truth**: 규칙·스킬은 여기 한 곳, 에이전트별로는 포인터만.
2. **Context Window 최적화**: Router(global_rule) → 필요한 문서만 로드.
3. **Progressive Disclosure**: 스킬은 description → SKILL.md → references 순으로 필요한 만큼만 읽힘.
4. **HITL**: `human-rules/`는 인간이 에이전트 산출물을 검증하는 통제 계층.
