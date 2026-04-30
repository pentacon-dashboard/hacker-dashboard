# B2B PB/WM 워크스테이션 전환 요약

- run_id: `20260430-012007-b2b-pb-workstation`
- branch: `dorec/harness-20260430-012007-b2b-pb-workstation`
- 배포 기준 순서: 로컬 Postgres 검증 -> Neon migration -> Fly backend -> Vercel frontend

## 구현 범위

- DB 모델에 `client_id`를 추가했다: `holdings`, `portfolio_snapshots`, `watchlist_alerts`.
- Alembic `007_b2b_multi_client` migration을 추가했다. 기존 row는 `client-001` 기본값을 유지하고, snapshot unique key는 `user_id/client_id/snapshot_date`로 확장했다.
- `user_id` 기본 데모 식별자는 `pb-demo`로 두고, 기존 `demo` row 조회 fallback을 유지했다.
- 포트폴리오 API에 optional `client_id` 필터를 추가했고 위험 문자열은 422로 차단하도록 검증을 추가했다.
- `GET /portfolio/clients`와 `POST /portfolio/reports/client-briefing`을 추가했다.
- Analyzer/portfolio summary에 `client_context`, `report_script`, `sector_breakdown`을 추가했다.
- 주요 티커 GICS 섹터 매핑과 deterministic drift helper를 추가했다.
- 프론트 `/`와 `/portfolio`를 PB 고객 선택, 고객별 조회, GICS 섹터 뷰, 브리핑 리포트 모달, 인쇄/다운로드 동작 중심으로 전환했다.
- API 계약 변경 후 `shared/openapi.json`, `shared/types/api.ts`를 갱신했다.

## 로컬 DB 검증

- `docker compose up postgres redis -d`: 통과
- Windows 호스트에서 `asyncpg`가 `localhost:5432` 연결 중 끊겨, 백엔드 컨테이너 내부에서 migration을 검증했다.
- `docker compose run --rm --no-deps -e DATABASE_URL=postgresql+asyncpg://hacker:hacker@postgres:5432/hacker_dashboard backend alembic upgrade head`: `002`에서 `007_b2b_multi_client`까지 통과
- `alembic_version`: `007_b2b_multi_client`
- `holdings`, `portfolio_snapshots`, `watchlist_alerts`의 `client_id`: `NOT NULL`, 기본값 `client-001`
- Docker 백엔드 `/health`: DB/Redis `ok`
- Docker 백엔드 `/portfolio/summary`, `/portfolio/clients`, `/portfolio/reports/client-briefing`: 응답 확인
- `client_id` NUL 입력: 포트폴리오 query/report body 모두 500 대신 422 확인

## 검증 결과

- `cd backend && uv run pytest tests/api/test_portfolio.py tests/api/test_rebalance_endpoint.py tests/unit/test_portfolio_services.py -q`: 60 passed
- `cd backend && uv run pytest tests/api/test_portfolio.py tests/api/test_rebalance_endpoint.py tests/unit/test_portfolio_services.py tests/unit/agents tests/golden -q`: 197 passed, warning 1
- `cd backend && uv run ruff check app tests`: 통과
- `cd backend && uv run alembic upgrade head --sql`: 통과
- `cd backend && uv run python -m app.export_openapi`: 통과
- `cd frontend && npm run gen:api`: 통과
- `cd frontend && npm run typecheck`: 통과
- `cd frontend && npm run test`: 287 passed, 1 skipped
- `cd frontend && npm run lint`: 통과
- `cd frontend && npm run build`: 통과
- `cd frontend && npx playwright test e2e/portfolio.spec.ts e2e/rebalance.spec.ts e2e/smoke.spec.ts --config=e2e/playwright.config.ts`: 9 passed, 2 skipped

## 계약 테스트 상태

- `cd backend && CONTRACT_BASE_URL=http://localhost:8000 uv run pytest tests/contract/test_openapi.py -q --tb=short`: 20 failed, 33 passed
- 이번 변경으로 추가된 `client_id` 위험 입력 500은 제거했다.
- 남은 실패는 주로 기존 전역 계약 이슈다: custom validator가 OpenAPI schema로 표현되지 않는 요청, multipart fuzz body, SSE 응답 schema, unknown query property 허용, 일부 copilot/watchlist overflow 500.
- Neon/Fly/Vercel 배포 전에는 전체 contract를 별도 스프린트로 정리하거나, 최소한 B2B 신규/변경 endpoint 중심의 smoke gate를 분리하는 것이 필요하다.

## 운영 배포 체크리스트

1. Neon 운영 DB에는 직접 개발 연결하지 않고, 검증된 `007_b2b_multi_client` migration만 적용한다.
2. Neon migration 직후 `alembic_version`과 세 테이블의 `client_id` 컬럼/default/index를 확인한다.
3. Fly backend를 배포하고 `/health`, `/portfolio/summary`, `/portfolio/clients`, `/portfolio/reports/client-briefing`을 확인한다.
4. Vercel frontend를 배포하고 `/`, `/portfolio`, 리포트 모달, 기존 `client-001` fallback을 확인한다.
5. 실제 운영 배포 전에는 contract 잔여 실패가 릴리스 차단인지, 별도 기술부채인지 판단해야 한다.
