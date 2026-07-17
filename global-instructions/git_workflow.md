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
- Always commit with `--author="ssunny-agent <ai-agent@ssunny.me>"`.
- **No `Co-Authored-By` lines, no AI attribution footers.**
- Never `--force`, never `--no-verify`.

## Branch Strategy
- `main`: 배포 가능한 안정 브랜치. **직접 push 금지** — 사용자가 GitHub에서 직접 merge.
- `develop`: 개발 통합 브랜치. **PR의 base는 항상 develop.**
- `feat/<feature-name>`: 기능 단위 브랜치.
- `fix/<issue>`: 버그픽스 브랜치.

## Pull Request Rules
- PR 제목은 커밋 메시지 형식과 동일하게.
- 셀프 리뷰 후 PR 오픈.
- 여러 PR이 열려 있으면 의존성 순서(merge order)를 정리해 제시.
- 배포 전 `main` 머지는 반드시 사용자가 직접 수행.
- 상세 절차: `skills/global/push-pr/SKILL.md`
