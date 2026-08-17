# Git Workflow

## Commit Message (Angular Convention)
Format: `<type>(<scope>): <short summary>`

| Type | Usage |
|------|-------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없는 코드 구조 개선 |
| `docs` | 문서/주석 변경 |
| `style` | 포맷팅, 공백 등 코드 의미 없는 변경 |
| `test` | 테스트 코드 추가/수정 |
| `chore` | 빌드, 의존성, 설정 파일 변경 |

Example: `feat(dashboard): add real-time NLP score heatmap`

## Authorship (agents)
- 커밋 시 `--author`에 `agent-config.json`의 `commit.author` 값을 사용한다.
  파일이 없으면 임의로 정하지 말고 사용자에게 물을 것 — git 이력에 남은 다른
  사람의 정체성을 그대로 재사용하는 일은 없어야 한다.
- `commit.coAuthorTrailers`가 false면 `Co-Authored-By` 줄과 AI 서명 푸터 금지.
- Never `--force`, never `--no-verify`.

## Branch Strategy
브랜치 이름은 `agent-config.json`의 `git` 항목을 따른다. 아래는 그 기본값이다.

- `protectedBranches`(기본 `main`): 배포 가능한 안정 브랜치. **직접 push 금지.**
  `humanMergesProtectedBranches`가 true면 머지는 사용자가 GitHub에서 직접 수행.
- `prBaseBranch`(기본 `develop`): 개발 통합 브랜치. **PR의 base는 이 브랜치.**
- `feat/<feature-name>`: 기능 단위 브랜치.
- `fix/<issue>`: 버그픽스 브랜치.

## Pull Request Rules
- PR 제목은 커밋 메시지 형식과 동일하게.
- 셀프 리뷰 후 PR 오픈.
- 여러 PR이 열려 있으면 의존성 순서(merge order)를 정리해 제시.
- 배포 전 `main` 머지는 반드시 사용자가 직접 수행.
- 상세 절차: `skills/global/push-pr/SKILL.md`
