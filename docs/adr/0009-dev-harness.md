# ADR 0009: 개발 타임 멀티-에이전트 하네스 (Planner → Generator → Evaluator 루프)

**날짜:** 2026-04-20
**상태:** 확정(Accepted)
**결정자:** 전체 팀 (frontend-engineer / backend-engineer / analyzer-designer / integration-qa)

---

## 맥락 (Context)

Anthropic 엔지니어링 팀은 Opus 4.6로 4시간·$124에 브라우저 DAW를 자동 구현한 실험(2026-04)에서, 단일 에이전트 코딩의 두 구조적 한계를 보고했다:

1. **컨텍스트 불안(context anxiety)** — 컨텍스트 윈도우가 차면 조기 종료 경향. compaction으로도 해결 불가
2. **자기 평가 실패** — 자기 결과물을 관대하게 평가. 검증 가능한 테스트가 있어도 변하지 않음

이를 GAN에서 영감 받은 **생성자/평가자 분리** + **플래너 선행 확장** + **매 이터 Fresh context**로 돌파.

hacker-dashboard도 같은 문제를 갖는다: 공모전 MVP 범위가 빠르게 늘어나는데, 단일 Claude Code 세션으로 여러 피처를 연달아 구현하면 후반에 품질이 떨어지고, `ci-local`을 "통과시킨다"고 주장하지만 실제로는 실패 상태로 종료하는 케이스가 재현된다. 사람이 매번 재검증하는 비용이 누적된다.

현 프로젝트에는 루프 구조가 없다. 4개 역할 에이전트(frontend/backend/analyzer/integration-qa)와 `make ci-local|e2e|contract|test` 훅, 골든 샘플 회귀가 이미 있어 평가자가 재사용할 자산은 충분하다.

핵심 요구사항:
1. 피처 요청 한 줄로 자동 구현·자동 검증이 돌아가야 한다
2. 품질 지표가 **객관적**이어야 한다 (LLM 자기 주장이 아닌 make 훅 결과)
3. **종료 조건이 명확**해야 한다 — 점수 임계치 + 최대 반복횟수
4. **기존 역할 에이전트·테스트 자산을 재사용**한다 (중복 신규 작성 금지)
5. 비용·리스크 상한 보장: 하네스는 로컬 커밋까지만, 푸시·PR·main 머지는 사람

---

## 결정 (Decision)

세 개의 신규 서브에이전트 + 한 개의 오케스트레이션 스킬로 개발 타임 반복 루프를 구축한다.

### 아키텍처

```
/harness-run "feature X" [--threshold 8.0] [--max-iter 5]
   │
   ├─▶ harness-planner (opus, 1회)
   │     └─ plan.md + sprints/<id>/contract.md (pytest/vitest/playwright stub)
   │
   └─▶ for each sprint:
          repeat until normalized_score >= threshold OR iter >= max_iter:
              harness-generator (sonnet+Task)
                 │ 파일 글롭 룰 → frontend/backend/analyzer/qa 역할 위임 (최대 2개)
                 └─ feat/qa-harness-<run_id>-<sprint> 브랜치에 커밋
              harness-evaluator (sonnet)
                 ├─ make typecheck(2) / lint(1) / test(2) / contract(2) / golden(2) / e2e(1)
                 └─ eval-<sprint>-<iter>.json + attempt-summary (≤40줄)
          └─ passed: 머지 대기 | degraded: handoff-<sprint>.md
```

### 스코어링 루브릭 (10점 만점)

| 항목 | 가중치 | 훅 |
|---|---|---|
| typecheck | 2 | `make typecheck` (mypy + tsc) |
| lint | 1 | `make lint` (ruff + eslint) |
| unit | 2 | pytest (골든 제외) + vitest |
| contract | 2 | `make contract` (schemathesis) — BE 미기동이면 보류, 척도 비례 환산 |
| golden | 2 | `pytest tests/golden/` + `_last_run.json` diff 카운트 |
| e2e | 1 | `make e2e` — **binary-gate at iter == max_iter only** (플레이키 완화) |

### Fresh Context 원칙

- Generator는 매 이터 **독립 호출**. 과거 대화 접근 불가
- 유일한 과거 정보: `attempt-summary-<sprint>-<iter-1>.md` (≤40줄, 시도·거절 사유·가설)
- raw git diff, 전체 코드 덤프, 과거 Evaluator 주장 **전달 금지**

### Direction Pivot

3이터 연속 `score` 개선 ≤ 0.5이면 Evaluator가 `suggest_direction_pivot=true` 발행.
다음 이터 Generator는 "이전 접근 폐기, 전혀 다른 접근" 지시를 받는다 (기사의 10번째 이터 사례 재현).

### 인간 승인 경계

하네스는 다음을 **자동 수행하지 않는다** (CLAUDE.md 규약 준수):
- `git push` / PR 생성 / main 머지
- ADR 신규 작성 (피처 ADR은 사람이)
- `.env*` / 시크릿 파일 수정

### 파일 레이아웃

```
.claude/harness/<run-id>/         # .gitignore로 전체 제외 (로컬 전용)
docs/harness-runs/<timestamp>/    # git tracked, summary + 최종 eval만 복사됨
```

`.gitignore`의 `!` 재포함은 상위 디렉토리 제외 시 동작하지 않는 git 관용 때문에 `.claude/harness/` 전체 제외가 단순·안전하다. 사람이 볼 산출물은 `/harness-run` 스킬이 종료 시 `docs/harness-runs/<timestamp>/`로 복사한다.

---

## 결과 (Consequences)

**긍정적:**
- 사람 재검증 비용 축소. Evaluator의 객관 지표(make 훅 결과) 통과 후에만 사람 리뷰 필요
- 기존 4개 역할 에이전트 + make 훅 + 골든 샘플 **재사용** — 하네스는 오케스트레이션만 추가
- 컨텍스트 불안 제거: 매 이터 Fresh context 호출이라 이터 N이 이터 N-1의 잡음을 계승하지 않음
- 자기 평가 실패 방지: Generator/Evaluator 독립 LLM 호출로 관대 채점 구조적 차단
- `summary.md`가 피처별 구현 이력을 남겨 나중 ADR 작성 시 컨텍스트 제공

**트레이드오프:**
- 비용: 1 스프린트 × 5이터 × (Generator + 2역할 + Evaluator) ≈ Sonnet 15~40회 + Opus 1회. 피처 크기별 차이 큼
- Playwright 플레이키 영향 최소화를 위해 E2E를 binary-gate로 격리 → 중간 이터레이션에서 UI 회귀를 조기 탐지 못함
- 3이터 연속 정체 시 pivot 로직이 항상 더 나은 접근을 찾는 것은 보장 못함 — max_iter 도달 시 degraded 핸드오프
- 스프린트 간 **순차 실행**이 기본. 병렬 워크트리는 Phase 2 (이번 범위 밖)
- LLM-only 채점이라 **디자인·UX 주관 품질은 점수화 불가** — 검증 가능한 기술 지표만 채점

---

## 대안 기각 사유 (Alternatives Rejected)

| 대안 | 기각 이유 |
|---|---|
| (A) 단일 에이전트 루프 (Generator가 자기 평가) | 기사의 자기 평가 실패 문제 재현. 관대 채점으로 품질 수렴 불가 |
| (B) Generator/Evaluator 동기 대화 (스프린트 계약 협상) | 기사에서 권고했으나 현 프로젝트는 `shared/openapi.json`·`gates/*`·골든 샘플이 이미 계약을 인코딩. 협상 이터 2~3회가 낭비. **1-shot 리뷰**로 축소 |
| (C) 디자인 점수를 Playwright 스크린샷 + LLM 채점으로 추가 | 공모전 MVP에서 디자인 주관 품질보다 **수치 정확성**이 우선. 디자인 채점은 Phase 2 |
| (D) 매 이터 raw git diff 전달 | Fresh context 원칙 위반. 이전 이터의 잘못된 가정이 다음 이터로 전파 |
| (E) `.claude/harness/**`를 전부 git 트래킹 | 리포 크기 급증. 사람이 볼 summary.md만 docs/로 복사 |
| (F) `make ci-local` 한 번만 돌려 단일 점수 부여 | 실패 원인이 어느 단계(typecheck/unit/contract)에서 발생했는지 Generator에 피드백 불가 |

---

## 참조

- 계획 파일: `C:\Users\ehgus\.claude\plans\anthropic-cosmic-valiant.md`
- 영감 출처: Anthropic 엔지니어링 기사 "멀티-에이전트 하네스로 장시간 자율 코딩" (2026-04)
- 관련 파일:
  - `.claude/agents/harness-planner.md`
  - `.claude/agents/harness-generator.md`
  - `.claude/agents/harness-evaluator.md`
  - `.claude/skills/harness-run/SKILL.md`
  - `.gitignore` — `.claude/harness/` 제외
- 재사용 자산:
  - `Makefile` — typecheck / lint / test / contract / e2e / ci-local
  - `backend/tests/golden/` — 골든 샘플 회귀 기준
  - `shared/openapi.json` — FE↔BE 단일 계약
  - `.claude/agents/{frontend,backend,analyzer,integration-qa}-engineer.md` — 4개 역할 에이전트
