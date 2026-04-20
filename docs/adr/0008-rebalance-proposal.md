# ADR 0008: 리밸런싱 제안 기능 — 결정적 계산 + LLM 해석 분리

**날짜:** 2026-04-20
**상태:** 확정(Accepted)
**결정자:** 전체 팀 (frontend-engineer / backend-engineer / analyzer-designer / integration-qa)

---

## 맥락 (Context)

ADR 0007(포트폴리오 컨텍스트 개인화)로 분석은 개인화됐으나 여전히 **행동을 제안하지 않는다**.
심사위원 공통 질문 "에이전트가 실제로 뭘 해주나요?"에 답할 기능이 없는 상태다.

핵심 요구사항:
1. **수치 환각 불가**: 매매 수량·금액은 수학적으로 계산되어야 한다. LLM이 숫자를 만들어내면 안 된다.
2. **구체적 매매 수량**: "BTC를 팔아라" 수준이 아닌 "KRW-BTC 0.02 BTC 매도 (약 170만 원)" 수준.
3. **사용자 제약 반영**: 최소 거래금액, 단일 종목 비중 상한 등 현실적 제약 조건 처리.

LLM에 수치 계산을 맡기면 환각이 발생하고, LLM을 전혀 쓰지 않으면 해석적 맥락이 부족하다.
두 책임을 분리하는 설계가 필요하다.

---

## 결정 (Decision)

리밸런싱 계산을 **순수 Python 함수**로 구현하고, LLM은 **해석만** 담당하는 구조로 분리한다.

### 계산 계층 (`app/services/rebalance.py`)

```
calculate_rebalance_actions(holdings, prices, target, constraints) → list[RebalanceAction]
```

- LLM 미개입. 입력 → 출력이 결정적(deterministic).
- 알고리즘: 자산군별 drift 계산 → 동일 자산군 내 기존 holdings에서 매매 (신규 종목 추천 없음)
- `RebalanceConstraints`(최소 거래금, 단일 비중 상한, 분수 허용 여부) 적용

### 해석 계층 (`app/agents/analyzers/rebalance.py` — `RebalanceAnalyzer`)

- 계산 결과(actions, drift)를 입력받아 headline / narrative / warnings 생성
- 3단 게이트 내장:
  - `schema_gate`: LLMAnalysis Pydantic 파싱 성공 여부
  - `domain_gate`: narrative 최소 길이 + 금지어 부재 확인
  - `critique_gate`: narrative가 actions에 없는 종목을 언급하는지 regex self-check

### API 계약 (`POST /portfolio/rebalance`)

```
Request:  target_allocation (4개 자산군 비중), constraints
Response: actions[]         ← 항상 존재, 결정적
          llm_analysis      ← null 가능 (degraded 모드)
          meta.gates        ← 3단 게이트 통과 여부 노출
```

`llm_analysis` 가 null 이어도 `actions` 는 반환되어 핵심 가치(리밸런싱 수량)가 보존된다.

### FE (`RebalancePanel` 컴포넌트)

- 4개 슬라이더(한국주식 / 미국주식 / 암호화폐 / 현금) + 프리셋 3종(공격형/균형형/안정형)
- 합계 100% 배지: 초과/부족이면 노란/빨간, 정확히 100%이면 초록
- 합계가 100%가 아닐 때 "제안 받기" 버튼 `disabled`
- degraded 시 "LLM 해석 실패 — 계산된 액션은 유효합니다" 배너 표시
- 로컬스토리지 `hd.rebalanceTarget` 로 목표 비중 영속화

---

## 결과 (Consequences)

**긍정적:**
- 수치 환각 가능성 0. actions 의 수량·금액은 순수 수학 계산 결과다.
- LLM 장애 시에도 actions 는 반환 → 서비스 핵심 가치 degraded 모드로 보존.
- 322 pytest (서비스 26 + 엔드포인트 9 + analyzer 10 + 기타) + 17 vitest PASS.
- 골든 샘플 3종 (`rebalance_balanced` / `rebalance_crypto_heavy` / `rebalance_constraint_violation`) 으로 회귀 가드.
- 사용자 체험: "종목 이해"(Symbol 상세)에서 "행동 제안"(Portfolio 리밸런싱)으로 에이전트 가치 확장.

**트레이드오프:**
- 신규 종목 매수 추천 없음 — 기존 holdings 내에서만 조정. 포트폴리오에 없는 자산군은 drift 해소 불가.
- 실시간 시세가 없을 경우 avg_cost 로 폴백하므로 추정 금액 오차 발생 가능.
- `fx` 자산군은 현재 계산에서 0으로 고정 (v2 확장 예정).

---

## 대안 기각 사유 (Alternatives Rejected)

| 대안 | 기각 이유 |
|---|---|
| (A) LLM이 actions까지 생성 | 수량·금액 환각 위험. 심사위원에게 "수치 신뢰성" 설명 불가. |
| (B) 별도 `/analyze?mode=rebalance` | 기존 Router/Analyzer 파이프라인과 OpenAPI 계약 파편화. |
| (C) 실제 주문 실행 포함 | 규제(자본시장법) 및 책임 이슈. 제안 단계로 스코프 고정. |
| (D) FE에서 직접 계산 | 서버 측 holdings/가격 데이터에 접근 불가. 로직 중복. |

---

## 참조

- 계획 파일: `C:\Users\ehgus\.claude\plans\replicated-sauteeing-corbato.md`
- ADR 0007 (포트폴리오 컨텍스트 개인화): 이 ADR의 전제 조건
- 관련 파일:
  - `backend/app/services/rebalance.py` — 결정적 계산 순수함수
  - `backend/app/agents/analyzers/rebalance.py` — LLM 해석 + 3단 게이트
  - `backend/prompts/rebalance_system.md` — 시스템 프롬프트
  - `frontend/components/portfolio/rebalance-panel.tsx` — UI 컴포넌트
  - `frontend/lib/api/rebalance.ts` — API 래퍼
