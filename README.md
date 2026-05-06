# hacker-dashboard

`hacker-dashboard`는 PB/WM 투자 분석 업무를 위한 고객 포트폴리오 대시보드입니다. 고객 또는 브로커 CSV 파일을 업로드하면 보유 종목을 정규화하고, 결정론적 지표를 계산한 뒤, 근거가 붙은 인사이트와 고객 브리핑 자료를 제공합니다.

> 이 프로젝트는 투자 분석 보조 도구입니다. 보장 수익, 확정적인 가격 방향, 근거 없는 개인화 매수/매도 조언을 생성하지 않도록 게이트와 근거 규칙을 적용합니다.

## 운영 주소

| 서비스 | URL |
| --- | --- |
| 프론트엔드 | https://hacker-dashboard-fe.vercel.app |
| 백엔드 API | https://hacker-dashboard-api.fly.dev |
| Swagger | https://hacker-dashboard-api.fly.dev/docs |

Vercel 배포 고유 URL은 보호될 수 있으므로, GitHub README에서는 공개 별칭인 `hacker-dashboard-fe.vercel.app`를 기준 주소로 사용합니다.

## 프로젝트가 하는 일

`hacker-dashboard`는 PB가 고객 포트폴리오를 검토할 때 반복해서 처리하는 작업을 하나의 분석 흐름으로 묶습니다.

1. PB가 고객 또는 브로커 CSV 파일을 업로드합니다.
2. 시스템이 컬럼 의미를 자동 감지하고, 불확실한 매핑은 PB 확인 대상으로 표시합니다.
3. 보유 종목을 고객, 계좌, 시장, 통화, 심볼 기준으로 정규화합니다.
4. 평가금액, 매입금액, 수익률, 자산 배분, 집중도, 리밸런싱 후보를 결정론적으로 계산합니다.
5. LLM은 이미 계산된 수치와 근거를 설명하는 역할만 수행합니다.
6. 대시보드, Copilot, 브리핑 흐름을 통해 PB가 고객 상담 자료를 준비할 수 있게 합니다.

## PB/WM 업무 흐름

| 업무 흐름 | 처리 내용 |
| --- | --- |
| 고객 CSV 온보딩 | 임의의 컬럼명을 표준 포트폴리오 필드로 매핑하고 신규 또는 기존 고객 데이터로 가져옵니다. |
| 매핑 검토 | `avg_cost`, `currency`, `market`처럼 불확실한 필드는 조용히 추정하지 않고 PB 확인 상태로 둡니다. |
| 포트폴리오 대시보드 | 보유 종목, 평가금액, 매입금액, 수익률, 자산 배분, 집중도, 신호 카드를 보여줍니다. |
| 리밸런싱 분석 | 목표 비중 대비 차이와 결정론적 매수/매도 후보를 계산합니다. |
| 근거 기반 인사이트 | 모든 숫자 주장이 입력 행, 계산 지표, API 데이터, 고정 테스트 데이터 중 하나 이상의 근거를 갖도록 요구합니다. |
| Copilot | 자연어 질문을 planner, comparison, simulator, news RAG 흐름으로 분해해 답변합니다. |

## 핵심 기능

- 범용 CSV 업로드: `symbol`, `quantity`를 핵심 필드로 보고, `avg_cost`, `currency`, `market`은 컬럼명과 종목 패턴으로 매핑하거나 추론합니다.
- PB 확인 흐름: 매입단가, 시장, 통화처럼 확신도가 낮은 필드는 자동으로 채우지 않고 검토 상태로 남깁니다.
- 고객 포트폴리오 정규화: 고객, 계좌, 시장, 통화, 심볼, 보유 수량, 평균단가를 공통 모델로 통합합니다.
- 결정론적 지표 계산: 평가금액, 매입금액, 수익률, 자산 배분, 집중도, 리밸런싱 후보를 코드로 계산합니다.
- Router/Analyzer: CSV 구조와 자산 패턴을 보고 주식, 코인, FX, 혼합 포트폴리오 분석 흐름을 선택합니다.
- Evidence gate: 숫자 인사이트와 보고서 문장은 입력 행, 계산 지표, API 데이터, 고정 테스트 데이터 중 하나 이상의 근거를 요구합니다.
- Copilot: 포트폴리오 질문, 비교, 시뮬레이션, 뉴스 기반 분석을 지원합니다.

## 스크린샷

| 고객 대시보드 | CSV 업로드와 매핑 흐름 |
| --- | --- |
| ![현재 고객 대시보드](docs/screenshots/current-dashboard.png) | ![현재 CSV 업로드 흐름](docs/screenshots/current-upload.png) |

## CSV 업로드

가져오기 흐름은 다음 필드를 핵심 필드로 봅니다.

| 표준 필드 | 예시 컬럼명 |
| --- | --- |
| `symbol` | `symbol`, `ticker`, `ticker symbol`, `stock code`, `종목코드`, `티커심볼` |
| `quantity` | `quantity`, `qty`, `holding qty`, `share count`, `보유수량`, `보유주식수`, `잔고수량` |

다음 필드는 선택 필드입니다. 있으면 정규화 품질을 높이고, 없거나 불확실하면 높은 확신도에서만 추론하거나 PB 확인 대상으로 남깁니다.

| 표준 필드 | 예시 컬럼명 |
| --- | --- |
| `avg_cost` | `avg cost`, `unit cost`, `purchase price`, `book price`, `매입단가`, `평균단가` |
| `currency` | `currency`, `ccy`, `currency code`, `통화`, `통화코드` |
| `market` | `market`, `exchange`, `market name`, `거래시장`, `시장` |

예시:

```csv
고객번호,계좌번호,거래시장,티커심볼,상품이름,보유주식수,매입단가,통화코드
client-001,acc-001,NASDAQ,AAPL,Apple Inc.,3,180,USD
```

## 아키텍처

```mermaid
graph TB
    PB["PB / WM 사용자"] --> CSV["고객 또는 브로커 CSV"]
    CSV --> Upload["업로드 API + 스키마 감지"]
    Upload --> Review["매핑 검토와 PB 확인"]
    Review --> Normalize["고객 / 계좌 / 보유 종목 정규화"]
    Normalize --> Metrics["결정론적 포트폴리오 지표"]
    Metrics --> Router["Router와 Analyzer 선택"]
    Router --> Gates["Schema / Domain / Evidence / Critique gates"]
    Gates --> UI["대시보드 / Copilot / 브리핑 근거"]

    UI --> FE["Next.js 프론트엔드"]
    Router --> BE["FastAPI 백엔드"]
    BE --> DB["Postgres + pgvector"]
    BE --> Cache["선택형 Redis"]
```

## 분석 가드레일

- 결정론적 서비스가 지표를 먼저 계산하고, LLM은 이미 계산된 결과를 설명합니다.
- 심볼, 시장, 컬럼 근거가 명확하면 Router 휴리스틱이 LLM 라우팅보다 우선합니다.
- 리밸런싱 후보는 LLM 설명이 저하 상태여도 결정론적으로 렌더링될 수 있어야 합니다.
- 숫자 인사이트와 브리핑 문구는 입력 행, 지표, API 데이터, 고정 테스트 데이터를 인용해야 합니다.
- 근거 또는 gate 검증이 부족하면 빈칸을 채우지 않고 저하 상태 또는 `insufficient_data` 상태를 반환합니다.

## 기술 스택

| 영역 | 스택 |
| --- | --- |
| 프론트엔드 | Next.js App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts, lightweight-charts, TanStack Query, Zustand |
| 백엔드 | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy async, LangGraph 스타일 에이전트 서비스 |
| LLM / 검색 | OpenAI SDK, planner/analyzer 프롬프트, pgvector 기반 뉴스 RAG |
| 데이터 | Postgres, pgvector, Redis 기반 선택형 캐시/세션 지원 |
| 인프라 | Vercel 프론트엔드, Fly.io 백엔드, Neon/Postgres 호환 데이터베이스 |
| 테스트 | pytest, Vitest, Playwright E2E, OpenAPI 계약 검증 |

## 로컬 개발

### 1. 사전 준비

- 프론트엔드 프로젝트와 호환되는 Node.js
- Python 3.12와 `uv`
- Postgres/Redis compose 구성을 위한 Docker Desktop

### 2. 환경 변수 설정

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Docker Compose에서 API 키나 공유 compose 변수가 필요하면 루트 `.env`도 생성합니다. `.env*` 파일은 커밋하지 않습니다.

### 3. Docker Compose로 실행

```bash
docker compose up --build -d
```

로컬 compose 데이터베이스에 마이그레이션을 적용합니다.

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard" uv run alembic upgrade head
```

데모 보유 종목을 적재합니다.

```bash
make seed-db
```

접속 주소:

- 프론트엔드: http://localhost:3000
- 백엔드 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

### 4. 서비스를 수동으로 실행

백엔드:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

프론트엔드:

```bash
cd frontend
npm install
npm run dev
```

## 검증

집중 검증:

```bash
cd backend && uv run pytest tests/unit/test_upload_service.py -q
cd backend && uv run pytest tests/integration/test_upload_api.py -q
cd frontend && npm run test -- components/upload/mapping-review-card.test.tsx
cd frontend && npm run typecheck
cd frontend && npm run lint
```

넓은 범위 검증:

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

## 배포

- 프론트엔드는 Vercel 프로젝트 `hacker-dashboard-fe`로 배포됩니다.
- 백엔드는 Fly.io 앱 `hacker-dashboard-api`로 배포됩니다.
- 백엔드 `/health`에서 `services.db != ok`이면 런타임 blocker로 봅니다.
- 연결된 데모 고객의 보유 종목이 0개이면, 빈 상태를 의도적으로 테스트하는 경우가 아닌 한 통과로 보지 않습니다.

운영 문서:

- [Fly.io 백엔드 배포](docs/ops/deploy-runbook.md)
- [Neon/Postgres 운영](docs/ops/neon-runbook.md)
- [프로덕션 배포 체크리스트](docs/ops/prod-deployment-checklist.md)

## 프로젝트 문서

- [Codex 프로젝트 지침](AGENTS.md)
- [투자 대시보드 스킬](.agents/skills/investment-dashboard/SKILL.md)
- [대회 Skills 진입점](Skills.md)
- [확장 대회 명세](.codex/competition/Skills.md)
- [Router 결정 노트](docs/agents/router-decisions.md)
- [아키텍처 ADR](docs/adr/)
- [데모 시나리오](demo/scenario.md)

## GitHub Actions 상태

[![CI](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/ci.yml)
[![계약 검증](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/contract.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/contract.yml)
[![E2E](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/e2e.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/e2e.yml)
[![프로덕션 Smoke](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/production-smoke.yml/badge.svg)](https://github.com/pentacon-dashboard/hacker-dashboard/actions/workflows/production-smoke.yml)
