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
│   ├── global/               ← 전역 스킬 (모든 프로젝트에서 사용, 저장소에 포함)
│   │   ├── catchup/              작업 재개 ("이어서 진행해")
│   │   ├── push-pr/              승인된 push/PR 워크플로우
│   │   ├── sync-docs/            문서·노션 동기화
│   │   ├── full-review/          전체 코드리뷰 + codex 교차 리뷰
│   │   ├── orchestrate/          서브에이전트·모델 티어링 정책
│   │   ├── server-runbook/       서버 페어 디버깅 (+ references/)
│   │   └── link-project-skills/  프로젝트 스킬 정션 자동 설정
│   └── projects/             ← 프로젝트 특화 스킬 (gitignore — 각자 로컬 전용)
├── templates/                ← 작업 유형별 구현 가이드 (필요 시 추가)
├── human-rules/
│   └── general_rule.md       ← 인간 검토용 체크리스트
└── README.md
```

`skills/projects/`는 개인 프로젝트에 종속된 스킬을 두는 곳으로, **gitignore 대상이라 저장소에 포함되지 않는다.** 각자 자기 프로젝트용 스킬을 로컬에서 만들어 쓰면 된다.

---

## 처음 설정하기 (최초 1회)

> **경로 원칙**: 이 저장소는 어디에 clone해도 된다. 저장소 안의 문서·스킬에는 절대경로를 쓰지 않는다 — 절대경로는 각 머신의 어댑터(아래 정션과 포인터 파일)에만 존재한다. 아래에서 `<ai-agents-root>`는 자신의 clone 위치로 치환.

### Claude Code

**1. 전역 스킬 연결** — 정션 하나로 전역 스킬 7개가 모든 프로젝트에서 활성화된다:

```
cmd /c mklink /J "%USERPROFILE%\.claude\skills" "<ai-agents-root>\skills\global"
```

(macOS/Linux: `ln -s "<ai-agents-root>/skills/global" ~/.claude/skills`)

이미 `~/.claude/skills` 폴더가 있다면 내용물을 옮기고 폴더를 지운 뒤 정션을 만든다.

**2. 전역 규칙 자동 로드** — `~/.claude/CLAUDE.md`에 아래 포인터를 넣는다 (경로만 자신의 clone 위치로):

```markdown
# Global rules

At the start of every session, read `<ai-agents-root>\global-instructions\global_rule.md`
and comply with it for the whole session. It routes to code style, git workflow,
security rules, and the skills index.
```

**3. 새 세션 시작** — 정션·포인터는 **새 세션부터** 반영된다. 이후 이 저장소를 수정하거나 `git pull` 하면 별도 작업 없이 즉시 반영된다.

**4. (선택) 프로젝트 특화 스킬** — 특정 프로젝트 전용 스킬이 필요하면 그 프로젝트에서 "이 프로젝트에 스킬 연결해줘"라고 하면 `link-project-skills` 스킬이 정션 생성부터 .gitignore 처리까지 자동으로 해준다.

### Codex

`~/.codex/AGENTS.md`에 동일한 3줄 포인터를 넣는다 (경로는 자신의 clone 위치로):

```markdown
At the start of every session, read `<ai-agents-root>\global-instructions\global_rule.md`
and comply with it. It routes to code style, git workflow, security rules, and the skills index.
```

Codex에는 스킬 자동 로드 기능이 없으므로, `global_rule.md`의 **SKILLS INDEX** 섹션이 라우터 역할을 한다 — 작업이 스킬에 해당하면 해당 SKILL.md를 읽고 따르게 되어 있다. (스킬 파일은 표준 markdown이라 어떤 에이전트든 읽을 수 있음)

### 기타 에이전트 (Antigravity 등)

자체 rules 파일에 같은 3줄 포인터를 넣으면 동일하게 동작한다.

---

## 스킬 사용법

설정이 끝났다면 쓰는 방법은 두 가지다:

1. **자동 트리거** — 그냥 평소처럼 말하면 된다. 각 스킬의 description에 트리거 조건이 정의되어 있어서, "이어서 진행해"라고 하면 `catchup`이, 서버 로그를 붙여넣으면 `server-runbook`이 알아서 발동한다.
2. **명시적 호출** — Claude Code에서 `/catchup`, `/push-pr`처럼 슬래시 명령으로 직접 부를 수 있다.

스킬이 목록에 안 보이면: ① 새 세션인지 확인 (정션 생성 직후엔 새 세션부터 반영) ② `~/.claude/skills` 정션이 살아있는지 확인 — `Get-Item ~\.claude\skills | Select LinkType, Target`

---

## 전역 스킬 상세

### `catchup` — 작업 재개

| | |
|---|---|
| **트리거** | "이어서 진행해", "계속 진행해", "뭐 하고 있었지", 세션 재개 |
| **호출** | `/catchup` |

git 상태(`status`/`log`/브랜치/열린 PR)와 `log_summary/{project}_dev_log.md`를 읽어 마지막 작업 지점을 복원한다. 한두 줄로 상태를 보고한 뒤 **묻지 않고 바로 이어서 작업**하고, 진행 후 dev_log를 갱신한다. "뭐 할까요?"라고 되묻지 않는 것이 핵심.

### `push-pr` — 승인된 push/PR 워크플로우

| | |
|---|---|
| **트리거** | "push 진행해", "PR 열어", "conflict resolve해", "머지 준비해" |
| **호출** | `/push-pr` |

push가 명시적으로 허가됐을 때의 표준 절차: Angular convention 커밋 + `--author="ssunny-agent <ai-agent@ssunny.me>"` 서명(co-author 금지), **PR base는 develop**(main 직접 push 금지 — main 머지는 사용자가 GitHub에서), PR 생성 후 머지 순서 제시, conflict resolve 절차, CI 확인까지. 이 스킬 없이는 push 금지가 기본 규칙.

### `sync-docs` — 문서/노션 동기화

| | |
|---|---|
| **트리거** | "문서 최신화", "노션에 반영", "log_summary 업데이트", "readme 업데이트" |
| **호출** | `/sync-docs` |

최근 변경을 파악한 뒤 3개 계층을 한 번에 동기화한다: ① repo 문서(README, docs/, plan) ② `log_summary/` dual-artifact(dev_log + summary) ③ Notion MCP로 프로젝트의 노션 페이지. 문서 작성 물량이 많으면 haiku 서브에이전트에 위임한다. 하나만 콕 집어 요청해도 나머지 계층이 뒤처져 있으면 같이 맞춘다.

### `full-review` — 전체 코드리뷰 + codex 교차 리뷰

| | |
|---|---|
| **트리거** | "전체 코드리뷰", "보안 점검", "codex 리뷰 돌려" |
| **호출** | `/full-review` |

브랜치 전체 diff 또는 열린 PR 전부를 스코프로 잡고, 보안(하드코딩된 시크릿, auth 누락, CORS 와일드카드, rate-limit, 인젝션) 중점으로 자체 리뷰 → 수정 적용 → `/codex:review`로 독립 교차 리뷰까지 돌린다. codex가 토큰 limit에 걸리면 대기 후 1회 재시도하고, 못 돈 PR은 명시적으로 보고한다.

### `orchestrate` — 서브에이전트/모델 티어링

| | |
|---|---|
| **트리거** | 대규모/병렬 작업 착수, "서브에이전트 써서", "토큰 아껴", "너는 조율만 해" |
| **호출** | `/orchestrate` |

비용 정책: 메인 에이전트는 조율·리뷰만, 구현 코딩은 **sonnet**, 문서·커밋·잡무는 **haiku**, 복잡한 설계만 opus/fable. 사용자 질문에 **먼저 답하고 나서** 백그라운드 위임(질문 방치 금지), 작업별 브랜치 분리(W1/W2 패턴), 서브에이전트가 죽으면 메인이 대신 짜지 말고 프롬프트 고쳐서 재기동.

### `server-runbook` — 서버 페어 디버깅

| | |
|---|---|
| **트리거** | SSH/터미널 출력 붙여넣기, "서버에서 뭐 돌려야 해", 배포/CD 문제 |
| **호출** | `/server-runbook` |

핵심 프로토콜: 사용자가 서버 출력을 붙여넣으면 **복붙 가능한 다음 명령만 코드블록으로** 간결하게 답한다(장황한 설명 금지, 파괴적 명령만 한 줄 경고). 프로젝트별 인프라 정보(서버 IP, 포트, compose 구성, 서비스 배치)는 `references/`에 분리되어 있어 명령 제안 전에 해당 파일을 먼저 읽는다. IPv6 `[::1]` 프록시, exFAT 권한, CORS, rate-limit 등 실제 겪은 함정 목록 포함.

### `link-project-skills` — 프로젝트 스킬 정션 설정

| | |
|---|---|
| **트리거** | "이 프로젝트에 스킬 연결해줘", "프로젝트 스킬 셋업" |
| **호출** | `/link-project-skills` |

새 프로젝트에 특화 스킬 폴더를 배선한다: ① `~/.claude/skills` 정션의 target에서 ai-agents 위치를 **동적으로 역산**(고정 경로 가정 없음) ② `skills/projects/<프로젝트>/` 생성 ③ `<프로젝트>/.claude/skills` 정션 생성 ④ 프로젝트 `.gitignore`에 `.claude/skills` 추가 ⑤ "새 세션부터 반영" 안내까지 자동.

---

## 스킬 추가/수정

- 전역 스킬: `skills/global/<이름>/SKILL.md` 생성 → `global_rule.md`의 SKILLS INDEX와 이 README에 한 줄 추가.
- 프로젝트 스킬: `skills/projects/<프로젝트>/<이름>/SKILL.md` 생성 (정션이 이미 있으면 그걸로 끝, 저장소에는 커밋되지 않음).
- 형식: YAML frontmatter(`name`, `description`) + 본문. **description이 트리거 조건을 결정**하므로 "언제 쓰는지"를 구체적인 사용자 발화 예시까지 포함해 적을 것. 긴 참고자료는 `references/`로 분리.

## 설계 원칙

1. **Single Source of Truth**: 규칙·스킬은 여기 한 곳, 에이전트별로는 포인터만.
2. **Context Window 최적화**: Router(global_rule) → 필요한 문서만 로드.
3. **Progressive Disclosure**: 스킬은 description → SKILL.md → references 순으로 필요한 만큼만 읽힘.
4. **HITL**: `human-rules/`는 인간이 에이전트 산출물을 검증하는 통제 계층.
