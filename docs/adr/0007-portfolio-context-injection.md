# ADR 0007: 포트폴리오 컨텍스트 개인화 주입

**날짜:** 2026-04-20
**상태:** 확정(Accepted)
**결정자:** 전체 팀 (frontend-engineer / backend-engineer / analyzer-designer / integration-qa)

---

## 맥락 (Context)

기존 Stock/Crypto/FX Analyzer 는 사용자가 보유한 포트폴리오를 전혀 참조하지 않고 시장 데이터만으로 분석을 수행했다. 이로 인해 두 가지 문제가 있었다.

1. **개인화 부재**: 동일 종목을 10주 보유한 사용자와 0주 보유한 사용자가 동일한 분석 결과를 받는다. 심사위원 질문 "왜 나한테 특별한가(Why this for me?)"에 답변 불가.
2. **집중도 리스크 무시**: 포트폴리오의 80%가 BTC 에 집중되어 있어도 Crypto Analyzer 는 시장 분석만 수행하고 집중도 경고를 제공하지 않는다.

공모전 MVP 로서 "임의 CSV → 자동 대시보드"라는 핵심 제안 가치에 개인화 레이어를 더해 기술적 깊이와 데모 임팩트를 동시에 강화해야 한다.

---

## 결정 (Decision)

`AnalyzeRequest` 에 `include_portfolio_context: bool = False` opt-in 플래그를 추가하고, 플래그가 True 일 때 다음 파이프라인을 실행한다.

```
POST /analyze (include_portfolio_context=true)
       │
       ▼
build_portfolio_context(db, user_id, target_market, target_code)
  └─ DB holdings 조회 → compute_summary(현재가·FX 환산) → PortfolioContext 구성
  └─ target 심볼 일치 holding → matched_holding 세팅
  └─ holdings 없으면 None (graceful degrade)
       │
       ▼
AgentState.portfolio_context = PortfolioContext.model_dump()
       │
       ▼
BaseAnalyzer._call(portfolio_context=...) → LLM payload 에 조건부 포함
  └─ portfolio_context=None 이면 payload 에 키 자체를 포함하지 않음
  └─ matched_holding 있으면 프롬프트 "사용자 포트폴리오 맥락" 섹션 활성화
       │
       ▼
Analyzer Output.evidence[] 에 source="portfolio.matched_holding" 항목 추가
       │
       ▼
캐시 키 = sha256(request_json + portfolio_hash[:16])
  └─ 동일 심볼 on/off 요청이 서로 다른 캐시 버킷을 사용
```

FE 에서는 로컬스토리지 키 `hd.includePortfolioContext` (기본 `true`)로 토글을 제어하며, `SymbolAnalysisSection` 컴포넌트에 "내 포트폴리오 반영" UI 토글을 노출한다. 응답에 `matched_holding` 이 있으면 `holding-badge` 와 `concentration-risk-alert` 를 렌더링한다.

---

## 결과 (Consequences)

**긍정적:**
- 보유 종목 분석 시 "5주 보유, 평균단가 $185 대비 현재 +4.1%" 같은 개인화 서술이 가능해진다.
- BTC 집중 포트폴리오 진입 시 집중도 경고를 자동 제공한다.
- 기본 `False` 유지로 기존 골든 샘플 21종 회귀가 보장된다.
- 캐시 키 분리로 포트폴리오 on/off 결과가 독립 TTL 을 가진다.
- 골든 샘플 2종 (`stock_with_portfolio.json`, `crypto_with_portfolio_concentration.json`) 으로 회귀 가드 추가.

**트레이드오프:**
- `include_portfolio_context=true` 요청은 DB 조회 + 현재가 API 호출이 추가되어 첫 응답 레이턴시가 증가한다 (캐시 MISS 기준 +300~500ms 예상).
- 현재 `user_id="demo"` 고정 — 실제 인증 연동 시 수정 필요.
- `compute_summary` 내 외부 가격 API 장애 시 holding 가격 계산 실패 → avg_cost 로 폴백 (graceful degrade).

---

## 대안 기각 사유 (Alternatives Rejected)

| 대안 | 기각 이유 |
|---|---|
| (a) 항상 포트폴리오 주입 (`include_portfolio_context` 플래그 없이) | 익명 사용자·CSV 분석 요청에 불필요한 DB 조회 발생. 캐시 오염 — 동일 시장 분석이 사용자마다 다른 캐시 키를 갖게 되어 히트율 급감. 프라이버시 설계 원칙 위반. |
| (b) 별도 엔드포인트 `/analyze/personalized` | Router/Analyzer/게이트 파이프라인 코드 중복. OpenAPI 계약 surface 증가. 캐시 로직 이중 관리. |
| (c) FE 에서 holdings 를 직접 /analyze payload 에 첨부 | 민감한 보유 정보가 클라이언트 → 서버 전송 과정에 노출. 서버 측 DB 신뢰 원칙 위반. |
