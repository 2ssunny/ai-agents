# AI-AGENTS — 에이전트 공용 지침 & 스킬 저장소

모든 AI 코딩 에이전트(Claude Code, Codex, Antigravity 등)가 공유하는 **규칙**과 **재사용 워크플로우(스킬)** 의 단일 원본(single source of truth).

각 에이전트에는 내용을 복사하지 않고 **링크/포인터만** 걸어둔다. 그래서 이 저장소에서 한 번 고치면 모든 에이전트에 즉시 반영된다.

---

## 처음 보는 사람을 위한 3분 설명

### 규칙(rule)이란

`global-instructions/global_rule.md` 하나가 **진입점(Router)** 이다. 에이전트는 세션 시작할 때 이 파일 하나만 읽고, 필요할 때 거기서 안내하는 다른 문서(코드 스타일, git 규약, 보안 규칙)로 넘어간다. 매번 전부 읽지 않으니 토큰이 절약된다.

### 스킬(skill)이란

**"이런 요청이 오면 이렇게 처리해라"를 적어둔 폴더** 하나다. 최소 구성은 이렇게 생겼다:

```
skills/global/catchup/
└── SKILL.md      ← YAML frontmatter(name, description) + 본문
```

`description`이 **언제 이 스킬이 발동할지**를 결정한다. 예를 들어 `catchup` 스킬의 description에 "이어서 진행해"가 들어있어서, 사용자가 그렇게 말하면 에이전트가 알아서 그 SKILL.md를 읽고 따른다. 사용자가 스킬 이름을 외울 필요는 없다.

스킬이 커지면 이렇게 확장된다 (`exam-prep`이 그 예):

```
skills/global/exam-prep/
├── SKILL.md          ← 진입점 (짧게 유지)
├── README.md         ← 사람이 읽는 설명
├── references/       ← 긴 상세 문서 (필요할 때만 읽힘)
├── scripts/          ← 실제 실행되는 CLI
├── schemas/          ← 데이터 검증 규칙
└── tests/            ← 스크립트 테스트
```

### 왜 링크로 연결하나

스킬 내용은 이 저장소 **한 곳에만** 존재한다. 프로젝트에는 그 폴더를 가리키는 링크만 생긴다. 에이전트마다 복사본을 두면 금방 서로 달라지는데, 링크는 그럴 일이 없다.

---

## 빠른 시작 (최초 1회)

> **경로 원칙**: 이 저장소는 어디에 clone해도 된다. 아래에서 `<ai-agents-root>`는 **자신이 clone한 실제 경로**로 바꿔 쓴다.
> Windows 예: `C:\dev\ai-agents` / macOS·Linux 예: `~/dev/ai-agents`

### 1단계 — clone

```bash
git clone https://github.com/2ssunny/ai-agents.git
cd ai-agents
pwd    # 여기서 나온 경로가 <ai-agents-root>  (Windows PowerShell은 `pwd` 대신 `$PWD`)
```

### 2단계 — 전역 규칙 연결 (포인터 파일 만들기)

에이전트가 세션 시작 시 `global_rule.md`를 읽게 만든다. **에이전트마다 파일 위치만 다르고 내용은 같다.**

| 에이전트 | 만들 파일 |
|---|---|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md` |
| Antigravity 등 | 해당 에이전트의 전역 rules 파일 |

파일에 이 3줄을 넣는다 (경로만 자신의 것으로):

```markdown
At the start of every session, read `<ai-agents-root>/global-instructions/global_rule.md`
and comply with it for the whole session. It routes to code style, git workflow,
security rules, and the skills index.
```

### 3단계 — 전역 스킬 연결 (Claude Code만)

Claude Code는 `~/.claude/skills`에 있는 스킬을 **모든 프로젝트에서** 자동으로 인식한다. 그 폴더를 이 저장소의 `skills/global`로 연결한다.

**Windows** (관리자 권한 불필요):
```cmd
cmd /c mklink /J "%USERPROFILE%\.claude\skills" "<ai-agents-root>\skills\global"
```

**macOS / Linux**:
```bash
ln -s "<ai-agents-root>/skills/global" "$HOME/.claude/skills"
```

> `~/.claude/skills`가 **이미 있으면** 위 명령이 실패한다. 안에 직접 만든 스킬이 있으면 먼저 `skills/global/`로 옮기고, 빈 폴더면 지운 뒤 다시 실행한다.

Codex와 Antigravity는 이 단계가 필요 없다. `global_rule.md`의 **SKILLS INDEX** 표가 스킬로 라우팅해주고, SKILL.md는 표준 markdown이라 어떤 에이전트든 읽을 수 있다.

### 4단계 — 연결 확인

```bash
# macOS / Linux
ls -l ~/.claude/skills          # → skills/global 을 가리키는 화살표가 보이면 성공
cat ~/.claude/CLAUDE.md         # → 3줄 포인터가 보이면 성공
```

```powershell
# Windows PowerShell
Get-Item "$HOME\.claude\skills" | Select-Object LinkType, Target   # LinkType = Junction
Get-Content "$HOME\.claude\CLAUDE.md"
```

**Claude Code를 새로 켠다.** 링크는 세션 중간에 인식되지 않고 **다음 세션부터** 반영된다. 그 다음부터는 저장소 쪽 수정이 즉시 반영된다.

---

## 프로젝트에 스킬 연결하기

가장 자주 하는 작업이다. 전역 스킬(3단계)은 이미 어디서나 쓸 수 있지만, **Codex·Antigravity에 스킬을 노출하거나** 프로젝트별 스킬을 붙이려면 프로젝트마다 링크가 필요하다.

작업할 프로젝트 폴더에서:

```bash
python3 <ai-agents-root>/skills/global/link-project-skills/scripts/link_project_skills.py \
    --project . --skill exam-prep --gitignore
```

만들어지는 것:

```
<프로젝트>/.agents/skills/exam-prep   → Codex, Antigravity가 읽음
<프로젝트>/.claude/skills/exam-prep   → Claude Code가 읽음
```

둘 다 저장소의 같은 폴더를 가리킨다. 복사본은 생기지 않는다.

### 자주 쓰는 옵션

| 옵션 | 언제 쓰나 |
|---|---|
| `--dry-run` | **뭘 할지 먼저 보고 싶을 때.** 파일을 전혀 건드리지 않는다. 처음이면 항상 이것부터 |
| `--skill 이름` | 연결할 전역 스킬. 여러 개면 `--skill a --skill b` |
| `--project-skills` | `skills/projects/<프로젝트명>/` 아래 스킬을 전부 연결 |
| `--gitignore` | 프로젝트 `.gitignore`에 링크 경로를 추가 (링크는 머신마다 달라서 커밋하면 안 됨) |
| `--agents claude` / `codex` | 한쪽 에이전트만 연결 |
| `--migrate` | 예전 방식으로 연결된 프로젝트를 변환 (아래 참고) |

전체 옵션은 `--help`로 볼 수 있다.

### 안전 장치

- **몇 번을 다시 돌려도 안전하다.** 이미 제대로 연결돼 있으면 `skipped`로 표시하고 넘어간다.
- **실제 폴더는 절대 지우지 않는다.** 자리에 진짜 폴더나 파일이 있으면 `rejected`로 보고만 하고 그대로 둔다. 옮길지 말지는 사람이 정한다.
- **링크를 지울 때 원본은 안 지워진다.** 링크만 끊는다.
- 결과가 `linked` / `skipped` / `replaced` / `rejected` 중 하나로 항상 표시된다. `rejected`가 하나라도 있으면 종료 코드가 0이 아니다.

Windows는 정션, macOS·Linux는 심볼릭 링크를 자동으로 고른다. Windows에서 심볼릭 링크가 안 되면 정션으로 자동 폴백하므로 개발자 모드가 꺼져 있어도 동작한다.

### 예전 방식으로 연결된 프로젝트

과거에는 `<프로젝트>/.claude/skills` **폴더 자체**가 `skills/projects/<프로젝트>`를 가리키는 정션이었다. 그 안에는 스킬별 링크를 만들 수 없다 (만들면 이 저장소 안에 파일이 생겨버린다).

스크립트가 이걸 감지하면 **아무것도 바꾸지 않고 알려만 준다.** `--migrate`를 줄 때만 정션을 풀고 (링크만 끊으며 중앙 내용은 그대로) 실제 폴더로 바꾼 뒤 스킬별로 링크한다. 예전 방식 프로젝트는 마이그레이션 전까지 그대로 잘 동작한다.

---

## 현재 스킬 목록

사용자가 스킬 이름을 부를 필요는 없다. 아래 "이럴 때 발동" 상황이면 에이전트가 알아서 찾아 쓴다.

### 전역 스킬 (`skills/global/`)

| 스킬 | 이럴 때 발동 |
|---|---|
| `catchup` | "이어서 진행해", "계속", 중단된 작업 재개 |
| `push-pr` | "push 해", "PR 열어" — 승인된 push/PR 절차 |
| `sync-docs` | "문서 최신화", "노션 업데이트" |
| `full-review` | "전체 코드리뷰", "보안 점검", codex 교차 리뷰 |
| `orchestrate` | "서브에이전트 써서", "병렬로", "토큰 아껴" |
| `server-runbook` | 서버 터미널 출력을 붙여넣거나 배포 문제 디버깅 |
| `exam-prep` | 강의노트·기출·해설로 시험 대비 노트/풀이집 만들기 |
| `link-project-skills` | "이 프로젝트에 스킬 연결해줘" |

`exam-prep`은 스크립트와 테스트를 포함한 큰 스킬이다. 자세한 사용법은 [`skills/global/exam-prep/README.md`](skills/global/exam-prep/README.md) 참고.

### 프로젝트별 스킬 (`skills/projects/<프로젝트>/`)

프로젝트 스킬은 `.gitignore`에 있어서 **clone하면 안 보인다** (내용이 사적이라 로컬에만 둔다). 새로 만들려면 `skills/projects/<프로젝트명>/<스킬명>/SKILL.md`를 만들고 `--project-skills`로 연결한다.

---

## 잘 안 될 때

| 증상 | 원인과 해결 |
|---|---|
| 스킬 목록에 안 나온다 | 링크 직후에는 반영되지 않는다. **에이전트를 완전히 껐다 켠다.** |
| `mklink` / `ln -s`가 "이미 존재한다"고 한다 | 그 자리에 폴더가 이미 있다. 내용을 확인해 옮기거나, 빈 폴더면 지우고 다시 실행 |
| 스크립트가 `rejected`를 냈다 | 그 자리에 **진짜 폴더/파일**이 있다는 뜻. 스크립트는 일부러 안 지운다. 직접 옮기고 다시 실행 |
| 규칙이 적용 안 되는 것 같다 | 포인터 파일 경로가 실제 clone 위치와 맞는지 확인 (`cat ~/.claude/CLAUDE.md`) |
| 프로젝트 규칙과 전역 규칙이 충돌한다 | 프로젝트 규칙이 우선한다. 다만 에이전트가 충돌을 감지하면 사용자에게 물어보게 돼 있다 |
| `link_project_skills.py`가 저장소를 못 찾는다 | 스크립트를 저장소 밖으로 복사하지 말 것. 자기 위치로 저장소를 찾는다 |

---

## 스킬 추가·수정

- **전역 스킬**: `skills/global/<이름>/SKILL.md` 생성 → `global_rule.md`의 SKILLS INDEX에 한 줄 추가.
- **프로젝트 스킬**: `skills/projects/<프로젝트>/<이름>/SKILL.md` 생성 → `--project-skills`로 연결.
- **형식**: YAML frontmatter(`name`, `description`) + 본문. `description`이 트리거 조건을 결정하므로 **"언제 쓰는지"를 구체적으로** 적을 것. 긴 참고자료는 `references/`로 분리.
- **플랫폼 전용 frontmatter 필드는 쓰지 않는다** — 같은 SKILL.md를 Claude Code·Codex·Antigravity가 모두 읽어야 한다.
- 실행 스크립트가 필요하면 `scripts/`에, 테스트는 `tests/`에 **스킬 폴더 안으로 자체 완결**시킨다 (`exam-prep` 참고). 표준 라이브러리 우선, 선택적 의존성은 없어도 동작하되 SKIPPED로 명확히 보고할 것.

---

## 구조

```
ai-agents/
├── global-instructions/
│   ├── global_rule.md        ← 진입점(Router). 모든 에이전트가 가장 먼저 읽음
│   ├── code_style.md         ← 코드 스타일 기준
│   ├── git_workflow.md       ← 커밋/브랜치/PR 전략 (--author 서명)
│   └── security_env.md       ← 시크릿/환경변수 규칙
├── skills/
│   ├── global/               ← 전역 스킬 (모든 프로젝트에서 사용)
│   │   ├── catchup/              작업 재개
│   │   ├── push-pr/              승인된 push/PR 워크플로우
│   │   ├── sync-docs/            문서·노션 동기화
│   │   ├── full-review/          전체 코드리뷰 + codex 교차 리뷰
│   │   ├── orchestrate/          서브에이전트·모델 티어링 정책
│   │   ├── server-runbook/       서버 페어 디버깅 (+ references/)
│   │   ├── exam-prep/            시험 대비 노트·검증된 풀이집
│   │   │                         (+ references/ scripts/ schemas/ tests/)
│   │   └── link-project-skills/  프로젝트 스킬 링크 (+ scripts/)
│   └── projects/             ← 프로젝트별 스킬 (.gitignore — 로컬 전용)
├── human-rules/
│   └── general_rule.md       ← 인간 검토용 체크리스트
└── README.md
```

---

## 설계 원칙

1. **Single Source of Truth** — 규칙·스킬은 여기 한 곳, 에이전트별로는 링크만.
2. **Context Window 최적화** — Router(`global_rule.md`) → 필요한 문서만 로드.
3. **Progressive Disclosure** — 스킬은 description → SKILL.md → references 순으로 필요한 만큼만 읽힘.
4. **HITL** — `human-rules/`는 인간이 에이전트 산출물을 검증하는 통제 계층.
5. **비파괴** — 자동화는 실제 내용을 지우지 않는다. 충돌하면 멈추고 보고한다.
