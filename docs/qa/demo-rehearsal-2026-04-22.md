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
- Q: "세션 메모리 저장소는?" → A: 기본 InMemoryStore. `COPILOT_SESSION_STORE=postgres` 로 Postgres 전환 가능.
