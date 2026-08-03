# exam-prep

강의노트·튜토리얼·교재·데이터시트·기출·공식해설로부터 **출처 근거가 있는 시험
대비 노트와 풀이집**을 만드는 전역 스킬. 열역학, 구조역학, 유체, 재료, 수학 등
STEM 과목 전반에서 쓴다.

핵심은 이거 하나야: **문서가 렌더링됐다는 게 계산이 검증됐다는 뜻이 아니다.**
생성과 검증을 구조적으로 분리하고, 최종 감사가 증거 없는 "검증됨"을 통과시키지
않는다.

## 뭘 하는 스킬인가

1. 입력 자료를 12개 클래스로 분류하고 (애매하면 `unclassified`로 남김)
2. 기출 분석으로 시험 범위·빈도·문제 유형·공식 분류(DS/MEM/DERIVE)를 뽑고
3. **개요를 사람에게 승인받고**
4. 하나의 캐노니컬 콘텐츠 모델을 만들어서
5. 문제를 독립적으로 풀고 공식 해설과 대조한 뒤 감사 레코드를 남기고
6. 그 모델에서 한영 혼용판과 영어 전용판을 **함께 생성**하고
7. PDF QA와 최종 완료 감사를 돌린다

## 캐노니컬 위치

```
ai-agents/skills/global/exam-prep/
```

내용은 여기 한 곳에만 존재해. 각 프로젝트에는 이 폴더를 가리키는 얇은 링크만
생긴다 — 복제본은 만들지 않아.

## 지원 에이전트

| 에이전트 | 인식 경로 |
|---|---|
| Claude Code | `~/.claude/skills/exam-prep` (전역 정션) 또는 `<프로젝트>/.claude/skills/exam-prep` |
| Codex | `<프로젝트>/.agents/skills/exam-prep` |
| Antigravity | `<프로젝트>/.agents/skills/exam-prep` |
| 그 외 | `MASTER_PROMPT.md`를 붙여넣으면 스킬 지원 없이도 동일하게 동작 |

frontmatter는 `name`과 `description`만 쓴다. 플랫폼 전용 필드가 없어서 어느
에이전트에서도 그대로 읽힌다.

## 처음 쓰는 경우 — 5단계

`<ai-agents>`는 이 저장소를 clone한 경로로 바꿔 쓴다. 저장소 전체 설치가 처음이면
[루트 README의 "빠른 시작"](../../../README.md#빠른-시작-최초-1회)을 먼저 보면 돼.

### 1. 학습 프로젝트 폴더를 만들고 자료를 넣는다

```
my-thermo-exam/
└── sources/          ← 강의노트, 튜토리얼, 데이터시트, 기출, 공식 해설을 전부 여기에
```

파일명은 안 바꿔도 돼. 스킬이 분류하고, 애매한 건 `unclassified`로 남겨서 확인을
요청한다.

### 2. 스킬을 프로젝트에 연결한다

```bash
cd my-thermo-exam
python3 <ai-agents>/skills/global/link-project-skills/scripts/link_project_skills.py \
    --project . --skill exam-prep --gitignore
```

처음이면 `--dry-run`을 먼저 붙여서 뭘 할지 확인하고 돌리는 걸 권한다. Claude Code는
`~/.claude/skills` 전역 정션이 있으면 이 단계 없이도 인식하지만, Codex·Antigravity는
`.agents/skills`가 필요하다.

> **레거시 주의**: 예전 방식은 `<프로젝트>/.claude/skills` **자체**가
> `skills/projects/<프로젝트>`를 가리키는 정션이었어. 그 안에는 스킬별 링크를
> 만들 수 없어 (만들면 ai-agents 레포 안에 파일이 생김). 스크립트가 감지해서
> 알려주고, `--migrate`를 줄 때만 실제 폴더로 바꿔줘. 정션 해제는 링크만 끊는
> 거라 원본 내용은 그대로 남아.

### 3. 환경을 점검한다 (선택이지만 권장)

```bash
python3 <ai-agents>/skills/global/exam-prep/scripts/doctor.py \
    --sources sources --output output --work-dir .agent-work/exam-prep
```

뭐가 없으면 뭘 못 하는지 알려준다. 아무것도 설치하지 않고, 파일도 안 건드린다.

### 4. 설정 파일을 복사한다 (선택)

```bash
cp <ai-agents>/skills/global/exam-prep/config.example.yaml ./exam-prep.yaml
```

과목만 바꿔도 충분해 (`profile: thermodynamics` / `structures` / `generic-stem`).
설정 없이 그냥 말로 시켜도 동작한다.

### 5. 에이전트에 말한다

에이전트를 **새 세션으로** 켜고 (링크는 다음 세션부터 인식됨) 평소처럼 요청하면 돼.
스킬 이름을 부를 필요는 없다.

```
열역학 시험 대비 노트 만들어줘. sources/에 강의노트, 튜토리얼, 데이터시트,
기출이랑 공식 해설 들어있어. 한국어 설명 + 영어 용어 버전이랑 영어 전용 버전
둘 다 필요해.
```

**Phase 2가 끝나면 에이전트가 멈추고 개요 승인을 요청한다.** 여기서 방향을 잡으면 돼 —
이후 작업량이 크니까 이 단계에서 확인하는 게 중요하다.

## 설정과 프로파일

설정은 `config.example.yaml`을 프로젝트로 복사해서 수정. 과목 프로파일은
`profiles/`에 generic-stem / thermodynamics / structures 세 개가 들어있어.

## 승인 체크포인트

Phase 2가 끝나면 **무조건 멈춘다.** 소스 인벤토리, 누락 자료, 범위 맵, 기출
매트릭스, 제안 개요, 페이지 배분, 공식 분류를 다 보여주고 사용자 결정을 기다려.

이미 승인한 계획이면 `approval.continue_without_approval: true`로 멈춤을 건너뛸
수 있는데, 승인 사실 자체는 여전히 `progress.json`에 기록돼야 해. 기록 없는
승인은 최종 감사에서 실패한다.

## 검증 ≠ 렌더링

이 둘은 완전히 다른 일이야.

| | 누가 판단하나 |
|---|---|
| 답이 맞는가? | 사람 또는 에이전트가 직접 풀어야 함. 스크립트 아님 |
| 푸는 작업을 실제로 했고 기록했는가? | `verify_evidence.py` |
| 증거가 실제 파일을 가리키는가? | `verify_evidence.py` |
| 과목이 요구하는 체크를 다 했는가? | `verify_evidence.py` |
| 텍스트가 바뀐 뒤에도 그 검증이 유효한가? | `verify_evidence.py` (콘텐츠 해시) |
| **이 문제의** 숫자가 맞는가? | 문제별로 직접 작성하는 검증 훅 |

스크립트 이름이 `verify_calculations.py`가 아니라 `verify_evidence.py`인 이유가
이거야. **임의의 공학 문제를 자동으로 풀 수 있는 범용 스크립트는 존재하지
않아.** 이 프레임워크는 문제별 검증 증거를 기록하고, 실행하고, 감사한다.

## 중단된 작업 재개

상태는 스킬 레포가 아니라 학습 프로젝트 안에 저장돼:
`<프로젝트>/.agent-work/exam-prep/` (경로 변경 가능).

```bash
python3 scripts/doctor.py --work-dir .agent-work/exam-prep        # 재개할 상태가 있나?
python3 scripts/validate_state.py --work-dir .agent-work/exam-prep # 체크포인트가 일관적인가?
python3 scripts/final_audit.py --work-dir .agent-work/exam-prep    # 실제로 뭐가 끝났나?
```

**output/에 PDF가 있다는 건 아무 증거도 아니야.** 검증 시작 전에 뽑은 초안일 수
있어. 진짜 진행도는 예제별 레코드 수, 증거를 갖춘 settled 수, 두 판본의 ID 일치
여부, 감사 통과 여부야.

## 감사 상태 읽는 법

검증 레코드 상태 7종:

| 상태 | 의미 | 문서에 실을 수 있나 |
|---|---|---|
| `VERIFIED` | 필수 체크 전부 통과 + 증거 있음 | O |
| `VERIFIED_WITH_ROUNDING_DIFFERENCE` | 반올림 차이만 있고 설명됨 | O |
| `OFFICIAL_SOLUTION_CORRECTED` | 공식 해설이 틀렸고, 기록됨 | O (다르다고 명시하고) |
| `ASSUMPTION_SENSITIVE` | 문제가 가정을 고정하지 않음 | 미해결로 표시해야 함 |
| `INSUFFICIENT_INFORMATION` | 주어진 자료로는 풀 수 없음 | 미해결로 표시해야 함 |
| `UNRESOLVED` | 작업했지만 결론 못 냄 | 미해결로 표시해야 함 |
| `NOT_YET_VERIFIED` | 아직 안 함 | 미해결로 표시해야 함 |

시각 검토는 **4개의 독립된 사실**로 나뉘고, 어느 하나도 다른 걸 함의하지 않아:
자동 preflight 통과 / 렌더 페이지 생성됨 / 자동 시각 휴리스틱 통과 / **사람이
실제로 봤음**. 마지막은 `record_human_review.py`를 사람이 직접 돌려야만 true가
된다. 컨택트 시트를 만든 건 검토가 아니라 검토를 가능하게 한 것뿐이야.

## 텍스트 보존

모든 산출물의 **원본은 텍스트**야. `canonical-content/`의 `.md`(본문) +
`.json`(구조)가 마스터고, DOCX/PDF는 거기서 파생된 결과물이라 언제든 지우고 다시
만들 수 있어. 상태·레코드는 키 정렬 고정 JSON이라 git diff가 깨끗하게 나와.

검증된 텍스트를 나중에 고치면 콘텐츠 해시가 안 맞아서 해당 레코드가 `stale`이
되고 최종 감사가 실패해. 고쳤으면 다시 검증하라는 뜻이지, 못 고친다는 뜻이 아냐.

## 스크립트

전부 `--help`, 의미 있는 exit code, 네트워크 호출 없음, 소스 파일 미변경.

| 스크립트 | 역할 |
|---|---|
| `doctor.py` | Phase 0 환경 점검 |
| `inventory_sources.py` | Phase 1 소스 분류 |
| `validate_profile.py` / `validate_manifest.py` / `validate_state.py` | 스키마·정합성 검증 |
| `verify_evidence.py` | 검증 증거 감사 + 문제별 훅 실행 |
| `check_parity.py` | 두 판본 캐노니컬 ID 일치 |
| `check_english_only.py` | 영어판 한글 혼입 검출 |
| `pdf_preflight.py` | 실제 페이지수·공백면·깨진 글리프 + 텍스트 사이드카 |
| `render_contact_sheet.py` | 페이지 이미지 + 컨택트 시트 |
| `record_human_review.py` | 사람 육안 검토 기록 (사람만 실행) |
| `final_audit.py` | 완료 게이트 종합 판정 |

exit code: `0` 통과, `1` 검사 실패, `2` 사용법 오류, `3` 선택적 의존성 없음
(SKIPPED), `4` 파일 읽기 실패.

## 의존성

표준 라이브러리만으로 전부 동작해. 선택적 패키지는 기능을 늘려줄 뿐 필수가 아냐.

| 패키지 | 없으면 |
|---|---|
| PyYAML | `.yaml` 프로파일/설정을 못 읽음 (같은 문서를 `.json`으로 주면 됨) |
| pymupdf | 페이지 렌더링 불가, PDF 텍스트 추출 불가 |
| pypdf 또는 pdfminer.six | (pymupdf 없을 때의 대안) PDF 텍스트 추출 |
| python-docx | `.docx` 생성 불가 |

PDF 리더가 하나도 없으면 페이지 수는 표준 라이브러리 폴백이 읽는데, 압축되지
않은 페이지 트리에서만 동작하고 확신이 없으면 **추측하는 대신 아무 값도 내지
않아**. 전역 설치는 하지 마 — 프로젝트 환경 안에서 설치해.

## 알려진 한계

- **답이 맞는지는 감사가 판단하지 못해.** 검증 작업이 수행·기록됐는지를 확인할
  뿐이야. 증거가 완전한 틀린 답도 모든 게이트를 통과해.
- 범용 스크립트로 임의의 공학 문제를 풀 수 없어. 실제 수치 검증은 문제별 훅에서
  일어나고, 그건 푼 사람이 직접 써야 해.
- 소스 분류는 파일명 휴리스틱이야. 보수적으로 동작하지만 사람이 검토해야 해.
- 공백 페이지 감지는 휴리스틱이야. 전면 도표는 텍스트 레이어상 공백과 구분이 안
  돼서, 실패가 아니라 사람에게 확인을 요청하는 경고로 나와.
- 범위 분석이 틀렸는지는 감사가 알 수 없어. 시험 범위인 주제를 범위 밖으로
  잘못 분류하면 감사에는 보이지 않아.
- 그림이 제대로 렌더링됐는지는 사람이 봐야만 알 수 있어.

## 테스트

```bash
cd skills/global/exam-prep
python3 -m unittest discover -s tests -t tests -v
```

표준 라이브러리 `unittest`만 쓰고 설치 의존성이 없어. 픽스처는 커밋된 바이너리가
아니라 매번 생성돼 — 실제 강의 자료처럼 보이는 파일을 레포에 두지 않기 위해서고,
테스트가 쓰는 PDF가 진짜 유효한 PDF이게 하기 위해서야.

## 문서

| 문서 | 내용 |
|---|---|
| `SKILL.md` | 진입점 — 활성화 조건, 워크플로우, 정직성 규칙 |
| `references/workflow.md` | 8단계 상세 |
| `references/source-policy.md` | 소스 분류·우선순위 |
| `references/scope-and-exam-analysis.md` | Phase 2 방법론 |
| `references/canonical-content-model.md` | ID 규칙과 캐노니컬 모델 |
| `references/problem-verification.md` | 검증 방법·레코드·훅 |
| `references/bilingual-generation.md` | 한영 혼용 스타일 |
| `references/document-style.md` | 문서 스타일 사양 (텍스트 기반) |
| `references/pdf-qa.md` | PDF QA와 4단계 시각 검토 |
| `references/recovery-and-checkpoints.md` | 중단 복구 |
| `references/completion-gates.md` | 완료 게이트와 최종 보고 |
| `MASTER_PROMPT.md` | 스킬 미지원 에이전트용 이식 프롬프트 |
| `examples/` | 최초 호출 / 승인 후 계속 / 중단 복구 / 최종 감사 |
