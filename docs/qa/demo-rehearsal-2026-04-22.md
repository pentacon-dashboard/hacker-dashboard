# 데모 리허설 체크리스트 — 2026-04-22

작성일: 2026-04-22
대상 심사: 공모전 최종 발표 (8분 시연)

## 준비 사항

- [ ] `make up` — Docker Compose 전체 스택 기동
- [ ] `make seed-db` — 데모 포트폴리오 시드 삽입
- [ ] BE 헬스체크: `curl http://localhost:8000/health | jq`
- [ ] FE 접속: `http://localhost:3000`
- [ ] Copilot stub 모드 확인: `COPILOT_NEWS_MODE=stub` (기본값)

---

## 시나리오 1: CSV 업로드 → 자동 대시보드 (2분)

- [ ] 헤더의 "파일 업로드" 버튼 클릭 → `demo/seeds/sample_portfolio.csv` 선택
- [ ] 업로드 완료 → Router 결정 근거 카드 표시 확인
- [ ] 포트폴리오 뷰 자동 전환 → 섹터별 도넛 차트, 리밸런싱 제안 렌더 확인
- [ ] 관전 포인트: Router가 CSV 컬럼 타입을 자동 인식해 Analyzer를 동적 선택하는 과정

## 시나리오 2: 워치리스트 + 실시간 시세 (1분)

- [ ] `/watchlist` 이동 → 심볼 검색으로 AAPL, TSLA 추가
- [ ] 시세 업데이트 (WebSocket ticks) 실시간 반영 확인
- [ ] 관전 포인트: Redis 캐시 + WS 스트림으로 5초 TTL 유지

## 시나리오 3: 리밸런싱 제안 (1분)

- [ ] 포트폴리오 → "리밸런싱" 탭 클릭
- [ ] 목표 비중 입력 → 제안 카드 렌더 (3단 게이트 통과 배지 확인)
- [ ] 관전 포인트: 도메인 게이트(가격 범위·시간 정합성) + critique 게이트 인용 검증

---

## KPI 스트립 & 포트폴리오 비중 설명 대사

> 이 섹션은 심사 현장에서 KPI 카드를 짚어가며 설명할 한 줄 대사 모음입니다.
> 특히 "집중도 리스크" 수치에 대한 질문이 예상되므로 아래 대사를 준비합니다.

### 집중도 리스크 카드 (HHI 기반)

**화면에 보이는 수치:** 12.4% — "양호"

**권장 대사:**

> "집중도 리스크는 HHI(허핀달-허쉬만 지수) 기반으로, 포트폴리오 내 단일 자산 편중을 정량화하는 지표입니다. 12% 는 10개 이상으로 분산된 양호한 상태예요."

**추가 해설 (Q&A 대비):**

- HHI 는 각 자산 비중의 제곱합 × 10,000 으로 계산합니다.
- 이 시스템에서는 `/100` 으로 % 로 정규화해 risk_score_pct 에 담습니다.
- 0~33%: 양호(분산), 33~66%: 보통, 66~100%: 집중 위험.

---

## Copilot 시나리오

> 전체 소요: 8분 (4분 기존 시나리오 + 4분 Copilot)
> 480초 기준 비트 시간표:

- **0:00–0:30** Copilot 커맨드바 소개: 헤더 오른쪽 검색창, `/?copilot=1` URL 파라미터로 강제 오픈
- **0:30–1:30** 단일 턴 쿼리: `"TSLA vs NVDA 비교"` 입력 → plan.ready → comparison_table + chart 카드 progressive 렌더
  - 관전 포인트: planner 가 DAG를 만들고 SSE 스트림으로 각 step 이벤트가 순서대로 들어오는 것 확인
  - 관전 포인트: step.gate 이벤트 3종(schema→domain→critique) 실시간 배지 표시
- **1:30–2:30** follow-up 쿼리: 같은 Drawer에서 `"그럼 엔비디아 -30% 시 내 포트폴리오?"` 입력 → simulator_result 카드 등장
  - 관전 포인트: 세션 메모리가 NVDA 컨텍스트를 carry-over 해 planner 가 1-step DAG로 단축
  - 관전 포인트: 1턴 comparison_table 카드가 히스토리에 남아 있음
- **2:30–3:30** degraded 시나리오: `/?copilot=1&mock_scenario=degraded` 접속 후 `"AAPL 최근 뉴스"` 입력
  - 관전 포인트: domain gate fail → degraded 배너 표시 + stub 모드 뉴스 카드 동시 렌더 (시스템이 graceful degradation)
  - 관전 포인트: "stub 모드" 배너가 카드 상단에 명시적으로 표시됨
- **3:30–4:00** ADR 0011/0012 1분 요약: SSE 선택 이유 + pgvector ivfflat 인덱스 + stub 기본값 의의

### 체크리스트 (데모 직전)

- [ ] `NEXT_PUBLIC_COPILOT_MOCK=1` 환경에서 `npm run test:e2e` 통과 확인
- [ ] `uv run pytest backend/tests/golden/test_copilot_end_to_end.py -q` exit 0
- [ ] `make -n copilot-demo` dry-run exit 0
- [ ] `docs/screenshots/copilot-query.png`, `docs/screenshots/copilot-final-card.png` 5KB 이상 확인

### 예상 질문 & 답변

- Q: "API 키 없이 어떻게 재현합니까?" → A: `COPILOT_NEWS_MODE=stub` 기본값 + fixture corpus. 실 키는 opt-in.
- Q: "RAG 인용 검증은?" → A: critique gate 의 citation faithfulness 체크. `source_url`이 ingest 테이블에 없으면 게이트 fail.
- Q: "세션 메모리 저장소는?" → A: 개발/데모 기본은 `COPILOT_SESSION_STORE=postgres` + `COPILOT_SESSION_STORE_URL` 기반 Postgres 지속 저장입니다. 테스트나 DB 없는 로컬 실행은 `COPILOT_SESSION_STORE=memory` 로 전환할 수 있습니다.
- Q: "목업에서 봤던 68.3% 와 지금 화면의 12.4% 는 왜 다릅니까?" → A: 목업의 68.3% 는 초기 와이어프레임에서 '입출금 위험 분석' 지표로 기획된 수치였습니다. 팀 결정으로 입출금 패턴 분석 대신 **HHI(허핀달-허쉬만 지수)** 기반 자산 집중도 리스크로 지표를 교체했습니다. HHI 는 단일 자산 편중을 정량화하는 산업 표준 지수로, 12.4%는 10개 이상 자산에 분산된 양호한 포트폴리오를 의미합니다. 두 지표는 측정 대상 자체가 다릅니다.
