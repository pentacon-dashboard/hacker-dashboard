# ADR 0011 — 자연어 Copilot: SSE 스트리밍 + 멀티스텝 오케스트레이션

| 항목 | 내용 |
|---|---|
| 상태 | 확정 (sprint-06) |
| 초안 | sprint-01 |
| 결정자 | backend-engineer, analyzer-designer |

---

## 맥락

Copilot 기능은 단일 REST 요청-응답 모델이 아닌, 여러 서브-에이전트를 순차/병렬 실행하는
멀티스텝 오케스트레이션 파이프라인이다. 사용자는 질의를 입력한 직후부터 각 단계의 진행
상황을 실시간으로 확인해야 하고, 심사위원은 "2초 내 첫 토큰, 전체 카드 progressive 스트림"
데모를 기대한다. 이를 위해 아래 세 가지를 결정해야 했다.

(a) 스텝 ID 예약어 정책 — `step_id="final"` 의미론적 충돌 방지.
(b) SSE vs WebSocket vs HTTP chunked 포맷 선택.
(c) 기존 router.py 와 신규 planner 의 공존 방식.

---

## 결정

### (a) `step_id="final"` 예약어 정책

`step_id` 값 `"final"` 은 **예약어**로 지정한다. 이 값은 최종 통합 게이트(schema→domain→critique)
단계를 식별하기 위해 오케스트레이터가 내부적으로 사용한다. 사용자가 작성한 step 이
`step_id="final"` 을 사용하면 **schema gate 가 즉시 reject** (HTTP 422 / SSE `error` 이벤트)
한다. 이유: final step 의 gate 이벤트는 `step_id="final"` 로 방출되므로, 동명의 사용자 step
이 존재하면 이벤트 스트림 소비자(FE)가 두 스텝을 구분할 수 없어 카드 렌더 충돌이 발생한다.

거부 메시지: `{"code": "RESERVED_STEP_ID", "detail": "'final' is reserved for the integration gate."}`

### (b) SSE data-only 포맷 선택 이유

SSE(Server-Sent Events) 의 `data:` 단일 라인 포맷을 채택한다. 대안은 `event:` 라인 분리,
WebSocket, HTTP/2 서버 push 였다.

선택 근거:
- **단순성**: `text/event-stream` 은 브라우저 기본 지원(`EventSource` API). 별도 클라이언트
  라이브러리 불필요.
- **프록시 호환성**: `event:` 라인을 사용하면 일부 CDN/리버스 프록시(Nginx, Cloudflare)가
  이벤트 타입을 기반으로 필터링·수정하는 경우가 있다. `data:` 단일 라인은 프록시 투명성이
  높다.
- **재접속 정책**: SSE 표준의 `retry:` + `id:` 필드로 자동 재접속을 지원하며, 마지막 수신
  이벤트 ID 기반 복구가 가능하다. WebSocket 은 재접속 시 전체 스트림 재요청이 필요하다.
- **단방향성 충분**: Copilot 질의는 단방향 스트림(서버→클라이언트)으로 충분하다. 동일 채널에서
  클라이언트→서버 메시지가 필요한 실시간 협업 등 양방향 시나리오는 현재 로드맵에 없다.
- **ASGI 통합 용이성**: FastAPI `StreamingResponse` + `async_generator` 조합이 SSE 에
  직접 매핑되며, `httpx.AsyncClient(app=...)` ASGI in-process 테스트에서도 SSE 스트림을
  그대로 소비할 수 있다.

### (c) 기존 router.py 와 신규 planner 공존 방식

기존 `backend/app/agents/router.py` 는 **단일 자산군 분석 라우터**로 유지한다. `/analyze` 엔드
포인트는 기존 router 경로를 그대로 사용한다. 신규 `planner.py` 는 **멀티스텝 복합 질의**
전용으로, `/copilot/plan` 및 `/copilot/query` 에서만 호출된다.

공존 기준:
- **단일 자산 + 단일 Analyzer**: `/analyze` → router.py → 기존 sub-graph (stock/crypto/portfolio/rebalance)
- **복합 질의** (comparison/simulator/news-rag 포함, 또는 2개 이상 Analyzer 체인): `/copilot/query`
  → planner.py → DAG 실행 → SSE 스트림

분기 결정 근거: router 를 planner 로 교체하면 기존 `/analyze` 테스트(sprint-01~03 harness)가
모두 깨진다. 공존 방식은 backward compatibility 를 보장하면서 Copilot 레이어를 **상위 추상**
으로 위치시킨다.

---

## 결과

- `step_id="final"` 예약어 정책이 schema gate 에 구현되어, 사용자 step 과의 충돌이 컴파일
  타임이 아닌 런타임(게이트)에서 조기 차단된다.
- SSE `data:` 포맷 채택으로 프론트엔드는 `EventSource` 또는 `fetch`+`ReadableStream` 두
  방식 모두로 스트림을 소비할 수 있다. CDN/리버스 프록시 환경에서 이벤트 필터링 리스크가
  최소화된다.
- router.py 와 planner.py 공존으로 기존 sprint-01~05 harness 가 sprint-06 통합 브랜치에서도
  그린을 유지한다. 향후 단일 자산 질의가 Copilot 채널로 들어와도 planner 가 1-step DAG 를
  생성해 기존 Analyzer 를 호출하는 통합 경로로 자연스럽게 이전 가능하다.
