# 공모전 데모 시나리오 (8분)

측정 기준: 스톱워치. 각 구간 경과 표시.

---

## 0:00 — 0:30 | 인트로

**발화:**
"한 화면에서 국내주식·해외주식·코인을 실시간 모니터링하고, LLM 이 자동으로 자산군을 판별해 분석합니다.
오늘 보여드릴 세 가지: 자동 Router 결정, 3단 품질 게이트, Lighthouse 90+ 완성도입니다."

**화면:** 대시보드 홈(`/`) — 포트폴리오 요약 카드 + 워치리스트 미리보기

---

## 0:30 — 1:30 | CSV 드롭 → Router 결정 → 분석 결과

**조작 순서:**
1. 홈 화면 드래그앤드롭 영역에 `demo/seeds/mixed.csv` 파일 드롭
2. Router 결정 근거 패널이 펼쳐지며 타이핑 애니메이션으로 표시되는 것 확인:
   - "국내주식 40% / 해외주식 30% / 코인 30% 혼합 감지"
   - "Stock Analyzer + Crypto Analyzer 병렬 실행"
3. 3단 게이트 배지 (Schema / Domain / LLM self-critique) 3개 모두 초록 체크
4. Analyzer 결과 카드 렌더 (섹터 배분 파이 + 요약 텍스트)

**강조 포인트:**
- 업로드 → 분석 완료까지 5초 이내 (캐시 히트 시 2초)
- 우상단 "Router 근거 보기" 토글로 의사결정 체인 원문 표시 가능

---

## 1:30 — 3:00 | 워치리스트

**조작 순서:**
1. 상단 네비게이션 > 워치리스트(`/watchlist`) 이동
2. 자산군 배지 (주식/코인/환율) 색상 구분 확인
3. 실시간 가격 tick: KRW-BTC 가격이 0.5초 간격으로 깜빡임
4. 스파크라인: 마우스 호버 시 최근 24시간 미니 차트 팝업
5. 필터: "코인만 보기" 클릭 → 주식 행 숨겨짐

---

## 3:00 — 5:00 | 종목 상세

**조작 순서:**
1. 워치리스트에서 `KRW-BTC` 행 클릭 → `/symbol/upbit/KRW-BTC`
2. TradingView 캔들 차트 + MA5/MA20 선 확인
3. 우측 패널: "Router 근거 토글" 버튼 클릭
   - 어떤 Analyzer 가 선택됐는지 (Crypto Analyzer)
   - 근거 인용 (시가총액, 24h 거래대금)
4. LLM 분석 카드: "강세 국면 / 단기 과열 주의" 요약 + 신뢰도 배지
5. **[개인화 시연]** 우측 상단 "내 포트폴리오 반영" 토글이 ON 상태임을 확인
   - 토글이 켜진 상태에서 분석 결과에 보유 배지 노출 확인:
     "AAPL 5주 보유 · 평균단가 $185 · 현재 +4.1% 수익"
   - `holding-badge` 가 분석 카드 상단에 표시되는 것 강조
   (토글 ON 시 실제로 AAPL 5주 보유 상태가 narrative에 반영됨 — 시드 데이터가 미리 삽입되어 있기 때문)
6. **[집중도 리스크]** BTC 시연 시 포트폴리오 내 BTC 비중이 80% 이상이면
   `concentration-risk-alert` 경고 배너 자동 노출
   - "현재 BTC 집중도가 80%를 초과합니다. 분산 투자를 고려하세요."
7. 토글 OFF 클릭 → holding-badge 와 경고 배너가 즉시 사라짐 확인
   (요청도 `include_portfolio_context=false` 로 재전송)

---

## 5:00 — 5:30 | 포트폴리오 진입 + 현황 확인

**조작 순서:**
1. 상단 네비게이션 > 포트폴리오(`/portfolio`) 이동
   → 이미 시드된 5종(삼성전자/AAPL/TSLA/BTC/ETH) 즉시 표시
2. 자산군 파이 차트로 "stock_kr / stock_us / crypto 분산" 시각 강조
3. 요약 카드 3종(총 투자금 / 평가금액 / 수익률) 확인
4. 손익 테이블: BTC 수익률 최상단으로 정렬 → 강조

---

## 5:30 — 6:30 | 리밸런싱 제안 시연

**조작 순서:**
1. 페이지 하단 "리밸런싱 제안" 섹션으로 스크롤
2. "공격형 70/30" 프리셋 버튼 클릭 → 슬라이더 자동 조정
   - 합계 100.0% 초록 배지 확인
3. "제안 받기" 버튼 클릭 → 2초 내 결과 렌더
4. 현재(파랑) / 목표(초록) / 예상(보라) 비교 차트: crypto 74% → 30% 축소 시각 강조
5. 액션 테이블: Sell KRW-BTC 0.02 BTC (빨강) + Buy AAPL 3주 (초록) 확인
6. LLM 해석 카드: "코인 집중도 리스크" 설명 + 양도소득세 경고 + 신뢰도 배지

**강조 포인트:**
- 수량·금액은 LLM이 아닌 수학 함수 계산 → 환각 구조적 불가능
- LLM이 실패해도(degraded) 액션 테이블은 그대로 표시

---

## 6:30 — 7:30 | 기술 차별점

**화면:** `docs/adr/` 또는 준비된 다이어그램 슬라이드

**발화:**
1. **Router/Analyzer 아키텍처**: LangGraph 서브그래프로 자산군별 독립 분석 체인 구성.
   Router 가 휴리스틱 100% 커버리지로 자산군을 판별, 적절한 Analyzer 를 동적 선택.
2. **3단 품질 게이트**: Zod/Pydantic 스키마 검증 → 도메인 sanity check → LLM self-critique.
   LLM 응답이 근거 없이 UI 에 직결되는 것을 원천 차단.
3. **캐시 히트율**: Redis 30분 TTL, 반복 분석 평균 응답 < 200ms.
4. **테스트 커버리지**: BE 322 pytest / FE 77 vitest / E2E 21 시나리오 / heuristic 100%.
5. **포트폴리오 컨텍스트 개인화** (ADR 0007):
   `include_portfolio_context=true` opt-in 플래그 하나로 DB holdings → PortfolioContext →
   AgentState → LLM payload 파이프라인이 활성화된다. matched_holding 이 있을 때만
   프롬프트에 개인화 섹션이 삽입되며, holdings 없음·API 장애 시 graceful degrade 로
   기존 분석으로 폴백한다. 캐시 키는 포트폴리오 해시를 섞어 on/off 버킷을 분리한다.
6. **결정적 계산 + LLM 해석 분리** (ADR 0008):
   리밸런싱 action 수치(수량·금액)는 순수 Python 함수 계산. LLM은 해석만 담당 →
   **수치 환각 구조적으로 불가능**. 3단 게이트가 narrative의 근거 인용을 검증한다.
   LLM 장애(degraded) 시에도 actions 는 항상 반환 — 서비스 핵심 가치 보존.

---

## 7:30 — 8:00 | 마무리

**화면:** Lighthouse 점수 스크린샷 (`docs/perf/final-scores.md`)

**발화:**
"Performance 90+, Accessibility 93+ 를 달성했습니다.
배포 URL: FE — https://hacker-dashboard.vercel.app / BE — https://hacker-dashboard-api.fly.dev
질문 받겠습니다."

---

## 리허설 체크리스트

- [ ] 스톱워치로 전체 8분 이내 완주
- [ ] 시드 파일 3종 (`stocks.csv`, `crypto.csv`, `mixed.csv`) 준비 완료
- [ ] 배포 URL 2곳 접속 가능 확인 (FE / BE)
- [ ] 예비 URL (localhost Docker Compose) 동작 확인
- [ ] 오프라인 시나리오 녹화본 (`demo/recording/`) 준비 (네트워크 장애 대비)
- [ ] "Router 결정 근거" 토글 동작 확인
- [ ] Lighthouse 점수 스크린샷 최신화 (`docs/screenshots/lighthouse-final.png`)
- [ ] 데모 계정 시드 데이터 삽입 (`make seed` 또는 `scripts/neon-setup.sql`)
- [ ] 발표 전 BE /health 200 응답 확인 (`scripts/healthcheck.sh`)
- [ ] `make seed-db` 완료 + `/portfolio/holdings` length == 5
- [ ] 프로덕션 Neon DB에도 동일 시드 완료 (`./scripts/run-prod-migration.sh`)
- [ ] Vercel 배포 URL 접속 시 포트폴리오 페이지 즉시 5종 표시
- [ ] `/portfolio` 하단 리밸런싱 패널 동작 확인 (슬라이더 + 합계 배지)
- [ ] 프리셋 3종 (공격형 70/30 / 균형형 / 안정형 30/70) 각각 "제안 받기" 응답 확인
- [ ] 리밸런싱 응답 3초 내 렌더 (latency_ms 로그로 확인)
- [ ] degraded 모드 (LLM 실패) 시 배너 표시 확인 — 개발자 도구 Network 탭에서 llm_analysis:null 시뮬레이션

---

## 비상 플랜

| 상황 | 대응 |
|------|------|
| 프로덕션 BE 다운 | `docker compose up -d` 로컬 fallback |
| 네트워크 없음 | 사전 녹화 영상 재생 (`demo/recording/`) |
| 차트 렌더 실패 | 스크린샷 슬라이드로 대체 (`docs/screenshots/`) |
| LLM 응답 지연 | 캐시된 분석 결과 노출 (Router 결정 근거 미리 고정) |
