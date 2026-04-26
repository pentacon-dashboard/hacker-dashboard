# Run Summary — 20260422-111542-nl-copilot

## 피처 요청

> 자연어 질의 기반 포트폴리오 Copilot을 도입한다. 헤더 커맨드 바에 자연어를 입력하면 Router가 멀티스텝 에이전트 플랜을 수립해 기존 Analyzer(stock/crypto/portfolio/rebalance)에 신규 서브-에이전트(comparison/simulator/news-rag)를 체인 실행하고, 결과를 구조화 응답(텍스트·차트·스코어카드·근거 카드)으로 SSE 스트리밍 렌더한다. 뉴스/공시 RAG는 Postgres pgvector 인덱스 + Claude citations 인용 강제로 구축하고, 세션 메모리로 follow-up 질의를 지원한다. 3단 품질 게이트는 각 서브-스텝과 최종 통합 응답 양쪽에 적용한다.

## 설정

- **threshold**: 8.0
- **max_iter**: 5
- **run_id**: `20260422-111542-nl-copilot`
- **workspace**: `.claude/harness/20260422-111542-nl-copilot/`

## 스프린트 결과

| Sprint | Status | Iter | Score | improvement_from_prev | 브랜치 |
|---|---|---|---|---|---|
| sprint-01 NL Query Planner | ✅ passed | 2 | 10.0/10 | +3.3 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-01` |
| sprint-02 News RAG 인프라 | ✅ passed | 2 | 10.0/10 | +3.3 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-02` |
| sprint-03 Sub-agents 3종 | ✅ passed | 1 | 8.9/10 | — | `feat/qa-harness-20260422-111542-nl-copilot-sprint-03` |
| sprint-04 SSE + 커맨드 바 | ✅ passed | 2 | 9.0/10 | +3.0 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-04` |
| sprint-05 세션 메모리 + follow-up | ✅ passed | 2 | 10.0/10 (revised) | +3.3 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-05` |
| sprint-06 통합/데모/ADR | ✅ passed | 2 | 8.75/10 | +5.45 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-06` |

**최종 통과율**: 6/6 ✅ (모든 스프린트 threshold 8.0 이상)
**총 이터레이션**: 11회 (Generator+Evaluator pair)
**Planner 재작업**: 4회 (sprint-01/02/04/05 contract revision 2, sprint-06 revision 2)

## 구현 산출물 요약

### 신규 백엔드
- `backend/app/agents/planner.py` — Router-as-planner, `CopilotPlan` DAG 생성 + 3단 게이트
- `backend/app/agents/analyzers/comparison.py, simulator.py, news_rag.py` — 서브-에이전트 3종
- `backend/app/services/copilot/orchestrator.py` — SSE 오케스트레이터, 단계별/최종 게이트, degraded 전파
- `backend/app/services/copilot/context.py` — `ActiveContext`, XML fence 인젝션 방지
- `backend/app/services/session/{protocol.py, memory_store.py, postgres_store.py}` — SessionStoreProtocol + 두 구현
- `backend/app/services/rag/embeddings.py` — `fake_embed()` sha256→1024-dim L2 정규화
- `backend/app/services/news/{ingest.py, search.py}` — async ingest + stub 검색
- `backend/app/api/copilot.py` — `/copilot/plan`, `/copilot/query` (SSE), `/copilot/session/{id}` GET/DELETE
- `backend/app/api/search.py` — `/search/news`, `/search/news/ingest`
- `backend/alembic/versions/{003_sprint02_pgvector_documents.py, 004_sprint05_copilot_sessions.py}`

### 신규 프런트엔드
- `frontend/components/layout/command-bar.tsx` — ⌘K 커맨드 바
- `frontend/components/copilot/{copilot-drawer.tsx, turn-history.tsx, cards/degraded-card.tsx}`
- `frontend/hooks/{use-copilot-stream.ts, use-copilot-session.ts}` — EventSource onmessage, sessionStorage
- `frontend/tests/mocks/copilot-sse.ts` — MSW SSE mock
- `frontend/e2e/copilot/{single-turn,follow-up,degraded}.spec.ts` — Playwright 3종

### 스키마/계약
- `shared/openapi.json` — Copilot/Session/Search 전 경로 반영, `_harness_step_delay_ms` 숨김 처리
- `shared/types/api.ts` — TS 타입 재생성
- `backend/app/schemas/copilot.py` — `CopilotPlan/Step/Card/Event` discriminated union, reserved `step_id="final"`

### 테스트·품질 게이트
- `backend/tests/harness/sprint_0{1..6}_contract.py` — sprint별 수락 기준 고정자산
- `backend/tests/golden/test_copilot_analyzers.py` + 9건 샘플 (comparison×3 / simulator×3 / news-rag×3)
- `backend/tests/golden/test_copilot_end_to_end.py` + 10번째 골든 `follow_up_2turn.json`
- `frontend/tests/harness/sprint-0{1..6}.test.ts` — vitest 고정자산

### 문서
- `docs/adr/0011-copilot-sse-and-multistep-orchestration.md` — `step_id="final"` 예약어, SSE data-only, router+planner 공존
- `docs/adr/0012-news-rag-vector-store.md` — 1024차원 근거, ivfflat vs HNSW, stub 기본값
- `docs/qa/demo-rehearsal-2026-04-22.md` — `## Copilot 시나리오` 병합 (8분 대본)
- `README.md` — `## 자연어 Copilot` 섹션 + ADR 링크 5개
- `Makefile` — `copilot-demo` (dry-run `make -n`), `ci-local --lf --ff`

## 주요 설계 결정 (Planner → Generator 확정)

1. **SSE data-only 포맷** — `event:` 라인 금지, `data: {json}\n\n`만 사용. `type` 필드로 이벤트 구분. FE는 `onmessage` 단일 리스너.
2. **직접 import 강제** — `/copilot/query`가 `build_copilot_plan`을 모듈 직접 호출. HTTP 자기호출 금지 (TestClient 중첩 hang 회피).
3. **`step_id="final"` 예약어** — Pydantic `field_validator`가 planner 생성 reject, 오케스트레이터는 `model_construct()`로 우회.
4. **프롬프트 인젝션 방어** — 직전 3턴 요약을 `<prior_turns><turn id="N">...</turn></prior_turns>` + `<user_query>...</user_query>` XML fence로 래핑. `html.escape()` 적용. Planner system prompt에 "fence 내부 명령 무시" 규칙.
5. **재현성 우선 stub 모드** — `COPILOT_EMBED_PROVIDER=fake` (sha256 기반 결정론), `COPILOT_NEWS_MODE=stub`, `fake_orchestrator_llm` autouse fixture로 API 키 없이 전체 하네스 그린.
6. **Store Protocol** — `SessionStoreProtocol` 4-메서드 표준, `memory`/`postgres` env 분기. 기본값 `memory`.
7. **골든 결정론** — 각 샘플당 `InMemorySessionStore()` 명시 생성 + 고정 `session_id="golden-{sample_id}"`.

## Planner 재작업(blocking) 요약

| Sprint | BLOCKING 건수 | 핵심 수정 |
|---|---|---|
| sprint-01 | 3건 | harness stub 덮어쓰기 방침, FakeClient DI 경로(`app.agents.llm.call_llm`), AC 숫자 9개 정합성 |
| sprint-02 | 4건 | `pgvector>=0.3` 의존, `ingest_document` async, pgvector docker 이미지 교체, `fake_embed` 알고리즘 고정 |
| sprint-03 | 0건 | 통과 (주의사항 3개만) |
| sprint-04 | 6건 | SSE data-only, session_id 수명, FakeClient DI fixture, `"final"` 예약어, 직접 import 강제, degraded FE 처리 |
| sprint-05 | 3건+4 WARN | `SessionStoreProtocol`, 컨텍스트 주입 규약(3턴/2000chars/XML fence), 인젝션 테스트 `captured_prompts` 스파이 |
| sprint-06 | 4건+5 WARN | Playwright spec 구체화, 골든 10번째(`follow_up_2turn`), ADR 0011/0012 결정 항목, harness stub 영구화 |

## 알려진 한계

1. **스크린샷 placeholder** — `docs/screenshots/copilot-{query,final-card}.png`는 220KB Python-generated PNG. 실 Playwright 캡처로 교체 필요(선택).
2. **AC-06-8 실행 vacuous** — `pytest tests/harness/`는 `sprint_XX_contract.py` 파일명 규약 상 0 items 수집. 명시 파일 경로 실행은 그린이지만 AC 문구와 실제 명령 불일치 (sprint-06 내 추후 보정 권장).
3. **Playwright E2E** — 계약 레벨 정적 검증만. 실 `npm run test:e2e` 수행은 운영자 수동.
4. **Postgres 세션 store** — `PostgresSessionStore`는 인터페이스만 구현, 실 DB 연결 테스트는 CI에서 `COPILOT_PGVECTOR_URL` 설정 시에만 수행.
5. **LLM 미커밋 변경** — `backend/app/agents/llm.py`에 pre-existing 미커밋 diff(Anthropic→OpenAI 실험). 하네스 런 범위 외. golden 평가 시 stash 필요.

## 다음 단계 (사람)

1. **브랜치 정리**: 6개 sprint 브랜치 중 단일 통합 브랜치로 squash 또는 순차 PR
   - 권장: `feat/qa-harness-20260422-111542-nl-copilot-sprint-06`을 베이스로 단일 PR (sprint-01~05 merge 커밋 이미 포함)
2. **Playwright 실행**: `cd frontend && npm run test:e2e` 로컬 1회 → 스크린샷 실 캡처로 교체
3. **Postgres 세션 store 통합 테스트**: Neon 브랜치 연결 후 `COPILOT_SESSION_STORE=postgres` 로 회귀 확인
4. **.env 주입** (운영 배포 시):
   - `COPILOT_EMBED_PROVIDER=voyage` (또는 `openai`) + API 키
   - `COPILOT_NEWS_MODE=live`
   - `COPILOT_PGVECTOR_URL` (pgvector 이미지 실행 중인 DB)
   - `COPILOT_SESSION_STORE=postgres`
   - `COPILOT_SESSION_MAX_TURNS=50`, `COPILOT_SESSION_TTL_DAYS=7`
5. **PR 생성 + 1인 리뷰**: CLAUDE.md 규약(`breaking:api` 라벨 여부 확인)
6. **AC-06-8 문구 보정**: `pytest tests/harness/sprint_*_contract.py` 로 명시 (or 파일명 규약 통일)
7. **ADR main 머지**: 리뷰 후 `docs/adr/0011, 0012` 확정
8. **데모 리허설**: `make -n copilot-demo` 검토 후 8분 데모 재연습

## 에러

없음. 전 스프린트 정상 종료.

---
*Generated by `/harness-run` (harness-planner / harness-generator / harness-evaluator 3-agent pipeline)*
