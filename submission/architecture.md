# 아키텍처 설명

## 핵심 아이디어

"임의 스키마 → 자동 분석 뷰" 를 가능하게 하는 세 가지 설계 결정:

1. **Router Meta Agent**: 입력 데이터를 먼저 분석해 자산군을 판별, 적합한 Sub Agent(Analyzer)를 동적 선택
2. **LangGraph 서브그래프**: 자산군별 분석 체인을 독립 노드로 구성, 병렬 실행 가능
3. **3단 품질 게이트**: LLM 응답이 검증 없이 UI 에 직결되지 않도록 방어층 구성

---

## 계층 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                Frontend (Next.js 15)                     │
│  CSV 업로드 → 대시보드 → 워치리스트 → 종목 상세 → 포트폴리오 │
│  TradingView 차트 / shadcn/ui / TanStack Query           │
│  "내 포트폴리오 반영" 토글 (hd.includePortfolioContext)   │
│  holding-badge / concentration-risk-alert 렌더링         │
└────────────────────────┬────────────────────────────────┘
                         │ OpenAPI 계약 (shared/openapi.json)
                         │ include_portfolio_context=true (opt-in)
┌────────────────────────▼────────────────────────────────┐
│                Backend (FastAPI)                          │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  build_portfolio_context(db, user_id, symbol)    │    │
│  │  DB holdings → compute_summary → PortfolioContext │    │
│  │  matched_holding 추출 / graceful degrade (None)   │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │ AgentState.portfolio_context    │
│  ┌──────────────────────▼───────────────────────────┐    │
│  │           Router Meta Agent (LangGraph)           │    │
│  │  스키마 분석 → 자산군 판별 → Analyzer 선택 → 집계   │    │
│  └──────┬──────────────┬──────────────┬────────────┘    │
│         │              │              │                   │
│  ┌──────▼──┐  ┌────────▼──┐  ┌───────▼──┐              │
│  │ Stock   │  │  Crypto   │  │   FX     │  ...          │
│  │Analyzer │  │ Analyzer  │  │ Analyzer │               │
│  │+portfolio│  │+portfolio │  │+portfolio│               │
│  └─────────┘  └───────────┘  └──────────┘              │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              3단 품질 게이트                          │ │
│  │  1. Pydantic v2 스키마 검증                          │ │
│  │  2. 도메인 sanity check (가격 범위·시간 정합성)        │ │
│  │  3. LLM self-critique + 근거 인용 검증               │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  Redis 캐시 (30min TTL)                                   │
│  캐시 키 = sha256(request + portfolio_hash[:16])          │
│  — on/off 독립 버킷으로 캐시 오염 방지                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Data Layer (Neon Postgres 16)                │
│  users / holdings / watchlist_items / portfolio_snapshots │
└─────────────────────────────────────────────────────────┘
```

---

## Router 결정 흐름

```
입력 CSV/질의
      │
      ▼
스키마 파싱 (컬럼명·값 패턴 분석)
      │
      ├─ 티커 패턴: KRW-* → crypto
      ├─ 거래소 필드: NYSE/NASDAQ → stock (US)
      ├─ 거래소 필드: KRX/KOSPI → stock (KR)
      ├─ 통화쌍 패턴: USD/EUR → fx
      └─ 혼합 → 다중 Analyzer 병렬 실행
      │
      ▼
선택된 Analyzer(s) 실행
      │
      ▼
품질 게이트 통과
      │
      ▼
응답 (분석 카드 + Router 근거 + 게이트 배지)
```

---

## 개인화 (포트폴리오 컨텍스트 주입)

`include_portfolio_context=true` opt-in 플래그로 사용자 보유 holdings 를 LLM 분석에 주입한다. FE 토글(기본 ON)로 사용자가 제어 가능하며, matched_holding 이 있을 때만 개인화 서술이 프롬프트에 포함된다. holdings 없음·API 장애 시 graceful degrade 로 기존 분석으로 폴백하며 에러가 전파되지 않는다. 골든 샘플 2종(`stock_with_portfolio.json`, `crypto_with_portfolio_concentration.json`)으로 회귀 가드를 구성했다.

---

## 리밸런싱 제안 (결정적 계산 + LLM 해석 분리)

**기술 차별점**: 수치 계산과 자연어 해석을 구조적으로 분리해 환각을 원천 차단한다.

```
[FE /portfolio 페이지]
  슬라이더 4개(한국주식/미국주식/암호화폐/현금) + 프리셋 3종(공격형/균형형/안정형)
  합계 100% 배지 / "제안 받기" 버튼 (합계 불일치 시 disabled)
        |
        | POST /portfolio/rebalance
        | { target_allocation, constraints }
        v
[/portfolio/rebalance 라우트 (FastAPI)]
  DB holdings + compute_summary → current_prices_krw
        |
        v
[services/rebalance.calculate_rebalance_actions()]   <-- 순수함수, 결정적, LLM 미개입
  자산군별 drift 계산 → 기존 holdings 내 매매 수량 산출
  RebalanceConstraints(최소 거래금·단일 비중 상한) 적용
        |
        | actions[], drift, expected_allocation
        v
[RebalanceAnalyzer.analyze()]                        <-- LLM 해석 + 3단 게이트
  schema_gate  : LLMAnalysis Pydantic 파싱
  domain_gate  : narrative 길이·금지어 검증
  critique_gate: narrative가 actions에 없는 종목 언급하는지 regex self-check
        |
        | llm_analysis (headline/narrative/warnings) | null (degraded)
        v
[RebalanceResponse]
  actions[]     <- 항상 존재, 수학적으로 정확
  llm_analysis  <- null 가능 (degraded 모드; 배너로 사용자에게 알림)
  meta.gates    <- 3단 게이트 통과 여부 투명 노출
```

- **리밸런싱 제안**: 결정적 계산(수학)과 LLM 해석(자연어) 분리 설계. 환각 불가능한 수치 기반 액션 제안.
- LLM 장애 시에도 actions 는 반환 — 서비스 핵심 가치(매매 수량) 보존.
- 골든 샘플 3종(`rebalance_balanced` / `rebalance_crypto_heavy` / `rebalance_constraint_violation`)으로 회귀 가드.

---

## 의사결정 기록

| 결정 | 이유 |
|------|------|
| FastAPI + LangGraph | 비동기 스트리밍 + 그래프 기반 에이전트 체인 |
| Next.js App Router | Server Component 로 초기 렌더 빠름 |
| Neon Postgres | 서버리스 분기(branch) 기능으로 preview/prod 분리 |
| Redis 캐시 30min | LLM 비용 절감 + 데모 응답 속도 보장 |
| OpenAPI 단일 진실 | FE/BE 계약 불일치 방지, TS 타입 자동 생성 |
| portfolio_context opt-in | 캐시 오염·프라이버시 보호 + 기존 회귀 방지 (ADR 0007) |
| rebalance 계산/해석 분리 | 수치 환각 원천 차단. LLM 장애 시에도 actions 보존 (ADR 0008) |

전체 ADR: [docs/adr/](../docs/adr/)
