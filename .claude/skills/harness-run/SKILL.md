---
name: harness-run
description: 개발 타임 자동 반복 하네스를 실행한다. 1~4문장 피처 요청을 받아 Planner → (Generator → Evaluator)* 루프를 돌리고, 점수 임계치(기본 8.0) 또는 최대 반복횟수(기본 5)에서 종료한다. 기능 자동 구현·회귀 검증이 필요할 때 호출.
---

# Skill — harness-run

Anthropic의 멀티-에이전트 하네스 기사(2026-04) 패턴을 hacker-dashboard 개발 타임에 적용합니다. 단일 에이전트의 컨텍스트 불안·자기 평가 실패 문제를 **Planner / Generator / Evaluator 분리** + **Fresh context 이터레이션**으로 해결합니다.

## 호출 방법

```
/harness-run <feature_request> [--threshold 8.0] [--max-iter 5] [--sprints-only <csv>]
```

**인자:**
- `feature_request` (필수): 1~4문장. 따옴표로 감쌀 것
- `--threshold` (기본 8.0): Evaluator `normalized_score`가 이 값 이상이면 해당 스프린트 종료
- `--max-iter` (기본 5): 한 스프린트당 최대 이터레이션. 도달하면 degraded로 표시하고 다음 스프린트 진행
- `--sprints-only` (옵션): "sprint-02,sprint-03" 형식. 기존 run_id 재개 시 특정 스프린트만 실행

**예시:**

```
/harness-run "헤더에 다크모드 토글을 추가한다. 선택은 localStorage에 저장되고 시스템 설정을 오버라이드한다."
/harness-run "포트폴리오에 Sharpe Ratio를 표시한다" --threshold 9 --max-iter 3
```

## 실행 흐름

```
run_id = $(date +%Y%m%d-%H%M%S)-<slug-of-feature>
workspace = .claude/harness/<run_id>/

mkdir -p $workspace/sprints $workspace/role-reports

# Phase 1: Planner (1회)
Task(harness-planner, {feature_request, run_id, workspace, threshold, max_iter})
  → produces plan.md + sprints/<id>/contract.md

# Phase 2: 스프린트별 루프
for sprint in sprints:
  if --sprints-only 지정되어 있고 sprint ∉ csv: continue

  # 2a. Evaluator 1-shot 계약 리뷰 (동기 대화 아님)
  Task(harness-evaluator, {run_id, sprint, mode: "review_contract"})
    → writes contract-review-<sprint>.md (경고·누락 항목만)
  # 리뷰 결과가 "BLOCKING"이면 Planner에 1회 피드백, 아니면 진행

  # 2b. 메인 루프
  iter = 0
  direction_pivot = false
  while iter < max_iter:
    iter += 1
    is_final_iter = (iter == max_iter)

    Task(harness-generator, {run_id, sprint, iter, workspace, direction_pivot})
      → writes gen-<sprint>-<iter>.md, role-reports/*.md, commits code

    Task(harness-evaluator, {run_id, sprint, iter, workspace, is_final_iter})
      → writes eval-<sprint>-<iter>.json, attempt-summary-<sprint>-<iter>.md

    eval = read eval-<sprint>-<iter>.json
    direction_pivot = eval.suggest_direction_pivot

    if eval.normalized_score >= threshold:
      break  # 스프린트 통과

  # 2c. 종료 처리
  if eval.normalized_score >= threshold:
    append to summary: {sprint, status: "passed", iter, score}
  else:
    write handoff-<sprint>.md (실패 원인, 재시도 힌트, 사람이 해야 할 것)
    append to summary: {sprint, status: "degraded", iter, score, handoff: "..."}

# Phase 3: 최종 요약
write $workspace/summary.md
copy $workspace/summary.md, 최종 eval-*.json → docs/harness-runs/<timestamp>/
```

## 종료 조건 (요약)

| 조건 | 결과 |
|---|---|
| `normalized_score >= threshold` | ✅ 스프린트 통과, 브랜치 머지 대기 |
| `iter >= max_iter` AND score < threshold | ⚠ degraded, handoff-*.md 작성 후 다음 스프린트 |
| 3이터 연속 score 개선 ≤ 0.5 | Evaluator가 `suggest_direction_pivot=true` → 다음 iter는 전혀 다른 접근 |

## 인간 승인이 필요한 지점

이 스킬은 **자동 실행하지 않는 것들**을 명시합니다. 아래는 스킬 종료 후 사람이 수동:

1. **브랜치 푸시** — 하네스는 로컬 커밋까지만. `git push -u origin <branch>`는 사람이
2. **PR 생성** — CLAUDE.md "최소 1인 리뷰" 규약 준수
3. **main 머지** — CI 통과 + 사람 승인
4. **ADR 작성** — 구조 결정이 포함된 피처면 `docs/adr/NNNN-*.md`를 사람이 추가
5. **.env / 시크릿 변경** — 하네스는 `.env*` 수정 금지

## 비용 가드

- 1 스프린트 × 5이터 × (Generator + 최대 2역할 위임) + Evaluator = 이터당 Sonnet 호출 3~5회
- Planner는 Opus 1회
- 기본값으로 한 `/harness-run` ≈ Opus 1회 + Sonnet 15~40회 + 역할 에이전트 호출
- **비용 상한 원하면:** `--max-iter 2` + `--sprints-only sprint-01` 로 부분 실행

## 파일 레이아웃

실행 중:
```
.claude/harness/<run-id>/
├── plan.md
├── sprints/
│   └── sprint-01/
│       └── contract.md
├── contract-review-sprint-01.md          # 1-shot review
├── gen-sprint-01-1.md
├── eval-sprint-01-1.json
├── attempt-summary-sprint-01-1.md
├── role-reports/
│   ├── backend-engineer-sprint-01-1.md
│   └── frontend-engineer-sprint-01-1.md
├── handoff-sprint-01.md                   # degraded 시만
└── summary.md
```

최종 보존 (git tracked):
```
docs/harness-runs/<YYYYMMDD-HHMMSS>/
├── summary.md
└── final-eval-<sprint>.json
```

## 실제 실행 절차

이 스킬을 호출받으면 다음 단계로 진행하세요:

### 1단계: 인자 파싱

```
feature_request = <사용자가 준 문자열>
threshold = <--threshold 값 or 8.0>
max_iter = <--max-iter 값 or 5>
sprints_only = <--sprints-only csv or null>
```

### 2단계: 워크스페이스 스캐폴드

```bash
cd C:/Users/ehgus/hacker-dashboard

slug=$(echo "$feature_request" | head -c 40 | tr -c 'a-zA-Z0-9' '-' | tr -s '-' | sed 's/^-\|-$//g')
# 한글·비ASCII만 있으면 slug가 비게 됨 — 해시 폴백
if [ -z "$slug" ]; then
  slug=$(echo "$feature_request" | cksum | awk '{print $1}' | head -c 8)
fi
run_id="$(date +%Y%m%d-%H%M%S)-${slug}"
workspace=".claude/harness/${run_id}"
mkdir -p "${workspace}/sprints" "${workspace}/role-reports"
```

### 3단계: Planner 호출

```
Task tool:
  subagent_type: harness-planner
  description: Plan feature harness run
  prompt: |
    feature_request: <원문>
    run_id: <run_id>
    workspace: <workspace>
    threshold: <threshold>
    max_iter: <max_iter>

    위 컨텍스트로 plan.md + 각 sprint contract.md를 작성하세요.
```

### 4단계: 스프린트별 루프

`<workspace>/plan.md`의 스프린트 섹션을 파싱해 sprint id 목록을 얻습니다. 각 스프린트에 대해:

**(a) 계약 1-shot 리뷰**

```
Task tool:
  subagent_type: harness-evaluator
  description: Review sprint contract
  prompt: |
    run_id: <run_id>
    sprint_id: <sprint>
    workspace: <workspace>
    mode: review_contract

    plan.md + contract.md를 읽고 누락·모호한 부분만 지적. contract-review-<sprint>.md 작성.
    BLOCKING 문제가 있으면 파일 첫 줄에 "STATUS: BLOCKING", 아니면 "STATUS: OK".
```

`contract-review-*.md` 첫 줄이 BLOCKING이면 Planner를 한 번 더 호출해 수정 후 진행. 두 번째도 BLOCKING이면 전체 중단하고 사용자에게 원인 보고.

**(b) 메인 루프**

pseudo code:
```
iter = 0
direction_pivot = false
while iter < max_iter:
  iter += 1
  is_final = (iter == max_iter)

  Task(harness-generator, {run_id, sprint, iter, workspace, direction_pivot})
  Task(harness-evaluator, {run_id, sprint, iter, workspace, is_final})

  eval = Read(workspace/eval-<sprint>-<iter>.json)  # JSON 파싱
  direction_pivot = eval.suggest_direction_pivot

  if eval.normalized_score >= threshold:
    passed = true; break
```

**(c) 종료 처리**

`passed=false`면 handoff 작성:

```
Write <workspace>/handoff-<sprint>.md:

# Handoff — <sprint>

## Status
DEGRADED — max_iter(<N>) 도달, 최종 score <score>/10

## 통과하지 못한 항목
<eval.failures 중 area별 대표 1건씩>

## 재시도 힌트
<eval.notes + 마지막 attempt-summary 주요 가설>

## 사람이 해야 할 것
1. 브랜치 feat/qa-harness-<run_id>-<sprint> 에서 수동 확인
2. 실패한 수락 기준 stub을 직접 디버그
3. (선택) /harness-run 재개: --sprints-only <sprint> --max-iter 3
```

### 5단계: summary.md + docs 복사

```
Write <workspace>/summary.md:

# Run Summary — <run_id>

## 피처 요청
<feature_request>

## 설정
threshold=<threshold>, max_iter=<max_iter>

## 스프린트 결과
| Sprint | Status | Iter | Score | 브랜치 |
| sprint-01 | passed | 2 | 9.0/10 | feat/qa-harness-<run_id>-sprint-01 |
| sprint-02 | degraded | 5 | 6.5/10 | feat/qa-harness-<run_id>-sprint-02 |

## 다음 단계 (사람)
1. passed 스프린트의 브랜치 → PR 생성 → 코드 리뷰
2. degraded 스프린트의 handoff-*.md 확인
3. 하네스 런 정리: /harness-run 재개 or 파일 정리
```

마지막에 `docs/harness-runs/<timestamp>/` 로 summary + 최종 eval만 복사 (전체 workspace는 .gitignore).

### 6단계: 사용자 보고

출력 텍스트 ≤100단어:

```
하네스 완료: run_id=<run_id>
- 스프린트 통과: <M>/<N>
- 총 이터레이션: <sum>
- 브랜치: feat/qa-harness-<run_id>-*
- 요약: docs/harness-runs/<timestamp>/summary.md

다음 단계: passed 브랜치 PR 생성, degraded 스프린트는 handoff 확인.
```

## 안전장치

- Planner/Generator/Evaluator 호출 실패 시 예외를 `summary.md`의 `errors[]`에 기록하고 그 스프린트만 건너뛰기
- `workspace` 디렉토리가 이미 존재하면 신규 run_id 생성 (덮어쓰기 금지)
- 사용자의 Ctrl+C로 중단되면 `summary.md`에 `"aborted": true` 기록
