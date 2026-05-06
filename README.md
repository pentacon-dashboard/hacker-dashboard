# hacker-dashboard

PB/WM 투자 분석을 위한 고객 포트폴리오 대시보드입니다. 고객 또는 브로커 CSV를 업로드하면 컬럼 스키마를 감지하고 보유 종목을 정규화한 뒤, 결정론적 지표와 근거 기반 LLM 설명을 함께 제공합니다.

> 투자 판단 보조용 도구입니다. 보장 수익, 확정적 가격 방향, 근거 없는 개인화 매수/매도 조언을 생성하지 않도록 게이트와 evidence 규칙을 둡니다.

## Production

| Service | URL |
| --- | --- |
| Frontend | https://hacker-dashboard-fe.vercel.app |
| Backend API | https://hacker-dashboard-api.fly.dev |
| Swagger | https://hacker-dashboard-api.fly.dev/docs |

Vercel의 배포 고유 URL은 보호될 수 있으므로 GitHub README에서는 public alias인 `hacker-dashboard-fe.vercel.app`을 기준 URL로 사용합니다.

## What It Does

`hacker-dashboard`는 PB가 고객 장부를 받았을 때 반복해서 하는 일을 한 화면의 분석 흐름으로 묶습니다.

1. 고객 또는 브로커 CSV를 업로드합니다.
2. 컬럼명을 자동 감지하고, 불확실한 필드는 PB 확인 대상으로 남깁니다.
3. 보유 종목을 고객/계좌/시장/통화 기준으로 정규화합니다.
4. 평가금액, 손익, 수익률, 배분, 집중도, 리밸런싱 후보를 결정론적으로 계산합니다.
5. LLM은 이미 계산된 수치와 evidence를 설명하는 데만 사용합니다.
6. PB는 대시보드, Copilot, 브리핑 근거를 보며 고객 대응 문맥을 정리합니다.

## PB/WM Workflows

| Workflow | What the project handles |
| --- | --- |
| Customer CSV onboarding | 임의 컬럼명을 표준 필드로 매핑하고 신규/기존 고객 장부로 import |
| Mapping review | `avg_cost`, `currency`, `market`처럼 불확실한 필드를 PB 확인 상태로 유지 |
| Portfolio dashboard | holdings, 평가금액, 손익, 수익률, 자산 배분, 집중도 신호 표시 |
| Rebalance analysis | 목표 비중 대비 drift와 매수/매도 후보를 deterministic service에서 계산 |
| Evidence-backed insight | 숫자 주장마다 입력 행, 계산 지표, API 데이터, fixture 중 하나 이상의 근거 요구 |
| Copilot | 자연어 질의를 planner, comparison, simulator, news RAG 흐름으로 분해해 스트리밍 응답 |

## Core Features

- 범용 CSV 업로드: `symbol`, `quantity`를 코어 필드로 보고, `avg_cost`, `currency`, `market`은 컬럼 별칭 또는 종목 패턴으로 매핑/추론합니다.
- PB 확인 흐름: 매입단가, 시장, 통화처럼 확신도가 낮은 필드는 자동으로 채우지 않고 확인 상태로 남깁니다.
- 고객 포트폴리오 정규화: 고객, 계좌, 시장, 통화, 보유 수량, 평균단가를 공통 모델로 통합합니다.
- 결정론적 지표 계산: 평가금액, 손익, 수익률, 자산 배분, 집중도, 리밸런싱 후보를 코드로 계산합니다.
- Router/Analyzer: CSV 구조와 자산 패턴을 보고 주식, 코인, FX, mixed 포트폴리오 분석 흐름을 선택합니다.
- Evidence gate: 숫자 인사이트와 보고서 문장은 입력 행, 계산 지표, API 데이터, fixture 중 하나 이상의 근거를 요구합니다.
- Copilot: 자연어 질의를 planner, comparison, simulator, news RAG 흐름으로 분해해 스트리밍 응답을 제공합니다.

## Screenshots

| Customer book dashboard | CSV upload and mapping flow |
| --- | --- |
| ![Current customer book dashboard](docs/screenshots/current-dashboard.png) | ![Current CSV upload flow](docs/screenshots/current-upload.png) |

## CSV Upload

필수 코어 필드는 두 개입니다.

| Standard field | 예시 컬럼명 |
| --- | --- |
| `symbol` | `symbol`, `ticker`, `ticker symbol`, `stock code`, `종목코드`, `티커심볼` |
| `quantity` | `quantity`, `qty`, `holding qty`, `share count`, `보유수량`, `보유주식수`, `잔고 수량` |

있으면 저장하고 없으면 추론 또는 PB 확인 대상으로 남기는 필드입니다.

| Standard field | 예시 컬럼명 |
| --- | --- |
| `avg_cost` | `avg cost`, `unit cost`, `purchase price`, `book price`, `매입단가`, `평균단가` |
| `currency` | `currency`, `ccy`, `currency code`, `통화`, `통화코드` |
| `market` | `market`, `exchange`, `market name`, `거래시장`, `시장` |

예시:

```csv
고객번호,계좌번호,거래시장,티커심볼,상품이름,보유주식수,매입단가,통화코드
client-001,acc-001,yahoo,AAPL,Apple Inc.,3,180,USD
```

## Architecture

```mermaid
graph TB
    PB["PB / WM user"] --> CSV["Customer or broker CSV"]
    CSV --> Upload["Upload API + schema detection"]
    Upload --> Review["Mapping review and PB confirmation"]
    Review --> Normalize["Client / account / holdings normalization"]
    Normalize --> Metrics["Deterministic portfolio metrics"]
    Metrics --> Router["Router and Analyzer selection"]
    Router --> Gates["Schema / Domain / Evidence / Critique gates"]
    Gates --> UI["Dashboard / Copilot / briefing evidence"]

    UI --> FE["Next.js frontend"]
    Router --> BE["FastAPI backend"]
    BE --> DB["Postgres + pgvector"]
    BE --> Cache["Redis optional"]
```

## Analysis Guardrails

- Deterministic services calculate metrics first; LLMs explain already-calculated results.
- Router heuristics based on symbols, markets, and columns win when the evidence is clear.
- Rebalance actions remain deterministic and should still render when LLM narrative is degraded.
- Numeric insight and briefing text must cite rows, metrics, API data, or fixtures.
- If evidence or gate verification is insufficient, the system returns degraded or `insufficient_data` behavior instead of filling gaps.

## Tech Stack

| Area | Stack |
| --- | --- |
| Frontend | Next.js App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts, lightweight-charts, TanStack Query, Zustand |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy async, LangGraph-style agent services |
| LLM / Search | OpenAI SDK, planner/analyzer prompts, news RAG with pgvector |
| Data | Postgres, pgvector, Redis optional cache/session support |
| Infra | Vercel frontend, Fly.io backend, Neon/Postgres-compatible database |
| Test | pytest, Vitest, Playwright E2E, OpenAPI contract checks |

## Local Development

### 1. Install prerequisites

- Node.js compatible with the frontend project
- Python 3.12 and `uv`
- Docker Desktop for Postgres/Redis compose setup

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

For Docker Compose, also create a root `.env` when API keys or shared compose variables are needed. Do not commit `.env*` files.

### 3. Run with Docker Compose

```bash
docker compose up --build -d
```

Then run migrations against the local compose database:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard" uv run alembic upgrade head
```

Seed demo holdings:

```bash
make seed-db
```

Open:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 4. Run services manually

Backend:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Verification

Focused checks:

```bash
cd backend && uv run pytest tests/unit/test_upload_service.py -q
cd backend && uv run pytest tests/integration/test_upload_api.py -q
cd frontend && npm run test -- components/upload/mapping-review-card.test.tsx
cd frontend && npm run typecheck
cd frontend && npm run lint
```

Broader checks:

```bash
cd backend && uv run pytest -q
cd frontend && npm run test
cd frontend && npm run build
make ci-local
```

E2E smoke:

```bash
cd frontend
npx playwright test e2e/smoke.spec.ts --config=e2e/playwright.config.ts
```

## Deployment

- Frontend deploys to Vercel project `hacker-dashboard-fe`.
- Backend deploys to Fly.io app `hacker-dashboard-api`.
- Backend `/health` with `services.db != ok` is a runtime blocker.
- Customer demo routes should not be treated as passing if linked clients have zero holdings unless the test explicitly targets an empty state.

Runbooks:

- [Fly.io backend deployment](docs/ops/deploy-runbook.md)
- [Neon/Postgres operations](docs/ops/neon-runbook.md)
- [Production deployment checklist](docs/ops/prod-deployment-checklist.md)

## Project Docs

- [Codex project instructions](AGENTS.md)
- [Investment dashboard skill](.agents/skills/investment-dashboard/SKILL.md)
- [Competition Skills entrypoint](Skills.md)
- [Expanded competition specification](.codex/competition/Skills.md)
- [Router decision notes](docs/agents/router-decisions.md)
- [Architecture ADRs](docs/adr/)
- [Demo scenario](demo/scenario.md)

## GitHub Actions

[![CI](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/ci.yml)
[![Contract](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/contract.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/contract.yml)
[![E2E](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/e2e.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/e2e.yml)
[![Production Smoke](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/production-smoke.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/production-smoke.yml)
