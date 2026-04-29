# hacker-dashboard

임의 투자 데이터 스키마에서 **자동으로 분석 뷰를 생성**하는 범용 금융 대시보드.

**공모전 차별점 3:**
1. **Router Meta Agent** — 업로드한 CSV 스키마를 분석해 자산군(주식/코인/환율/매크로)을 자동 판별, 적절한 Analyzer 를 동적 선택
2. **3단 품질 게이트** — LLM 응답이 검증 없이 UI 에 직결되지 않도록 스키마·도메인·self-critique 3단계 검증
3. **5초 자동 대시보드** — 임의 CSV 드롭 → 자산군 배지 + 분석 카드 + 실시간 차트 자동 구성

---

## 아키텍처

```mermaid
graph TB
    subgraph FE["Frontend (Next.js 15 + Vercel)"]
        Upload["CSV 업로드"]
        Dashboard["대시보드 렌더"]
        Charts["TradingView 차트"]
    end

    subgraph BE["Backend (FastAPI + Fly.io)"]
        Router["Router Meta Agent\n(자산군 판별)"]
        Gate["3단 품질 게이트\nZod/Pydantic → Domain → LLM"]
        subgraph Analyzers["Analyzers (LangGraph 서브그래프)"]
            StockA["Stock Analyzer"]
            CryptoA["Crypto Analyzer"]
            FxA["FX Analyzer"]
        end
        Cache["Redis 캐시\n(30min TTL)"]
    end

    subgraph Data["Data Layer (Neon Postgres)"]
        DB["hacker_dashboard DB"]
        Snap["Portfolio Snapshots"]
    end

    Upload -->|"OpenAPI 계약"| Router
    Router --> Gate
    Gate --> Analyzers
    Analyzers --> Cache
    Cache --> Dashboard
    Dashboard --> Charts
    BE --> DB
    BE --> Snap
```

---

## 기술 스택

| 계층 | 기술 |
|------|------|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, shadcn/ui, TradingView Lightweight Charts |
| Backend | FastAPI, LangGraph, Pydantic v2, Python 3.12 |
| LLM | Claude Sonnet 4.6 (기본), Opus 4.7 (고난도 분석) |
| Data | Neon Postgres 16, Redis 7 (캐시) |
| Infra | Docker Compose, Vercel (FE), Fly.io (BE) |
| 테스트 | pytest, vitest, Playwright, schemathesis |

---

## 3단 품질 게이트

```
입력 데이터
    │
    ▼
1. 스키마/타입 검증 ── Zod (FE) + Pydantic v2 (BE)
    │                   형식 오류, 필수 필드 누락
    ▼
2. 도메인 sanity check ── 가격 범위, 시간 정합성, 이상치 탐지
    │
    ▼
3. LLM self-critique ── 분석 근거 인용 검증, 할루시네이션 플래그
    │
    ▼
UI 렌더 (검증 배지 + 근거 출처 표시)
```

모든 단계 통과 시 초록 배지, 실패 시 오렌지/빨간 배지 + 원인 메시지.

---

## Router 결정 근거

Router 가 어떤 기준으로 Analyzer 를 선택하는지 전체 로직은 [router-decisions.md](docs/agents/router-decisions.md) 참조.

UI 에서 "Router 근거 보기" 토글로 의사결정 체인 원문 확인 가능.

---

## 스크린샷

| 페이지 | 미리보기 |
|--------|---------|
| 홈 / CSV 업로드 | `docs/screenshots/home.png` |
| 워치리스트 | `docs/screenshots/watchlist.png` |
| 종목 상세 | `docs/screenshots/symbol-detail.png` |
| 포트폴리오 | `docs/screenshots/portfolio.png` |
| Lighthouse | `docs/screenshots/lighthouse-final.png` |

---

## 로컬 실행

```bash
# 전제: Docker Desktop, .env 파일 (ANTHROPIC_API_KEY 주입)
cp frontend/.env.production.example frontend/.env.local
# ANTHROPIC_API_KEY 값 편집 후

docker compose up -d --wait

# 접속: http://localhost:3000 (FE), http://localhost:8000/docs (BE Swagger)
```

**Quickstart (5단계)**

1. Docker Desktop 실행
2. `docker compose up -d --wait`
3. `cd backend && DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard" uv run alembic upgrade head`
4. `make seed-db` — 데모 포트폴리오 5종(삼성전자/AAPL/TSLA/BTC/ETH) 삽입
5. http://localhost:3000 접속

시드 후 `/portfolio` 페이지에 5종 holdings가 보입니다.

`curl http://localhost:8000/health` → `{"status": "ok"}` 로 BE 정상 확인.

시드 CSV 업로드:
```bash
make seed
```

테스트 실행:
```bash
make test      # BE pytest + FE vitest
make e2e       # Playwright smoke
make contract  # schemathesis (서버 기동 중 필요)
```

---

## 배포 URL

| 서비스 | URL |
|--------|-----|
| Frontend (Vercel) | https://hacker-dashboard-fe.vercel.app |
| Backend API (Fly.io) | https://hacker-dashboard-api.fly.dev |
| API 문서 (Swagger) | https://hacker-dashboard-api.fly.dev/docs |

---

## 테스트 / 커버리지

[![CI](https://github.com/your-org/hacker-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/hacker-dashboard/actions/workflows/ci.yml)
[![Contract](https://github.com/your-org/hacker-dashboard/actions/workflows/contract.yml/badge.svg)](https://github.com/your-org/hacker-dashboard/actions/workflows/contract.yml)
[![E2E](https://github.com/your-org/hacker-dashboard/actions/workflows/e2e.yml/badge.svg)](https://github.com/your-org/hacker-dashboard/actions/workflows/e2e.yml)
[![Lighthouse](https://github.com/your-org/hacker-dashboard/actions/workflows/lighthouse.yml/badge.svg)](https://github.com/your-org/hacker-dashboard/actions/workflows/lighthouse.yml)

| 영역 | 수치 |
|------|------|
| Backend pytest | 276 통과 |
| Frontend vitest | 60 통과 |
| E2E Playwright | 13 시나리오 |
| Router heuristic 커버리지 | 100% |
| OpenAPI 스키마 | 1692 라인 |

---

## 팀 역할 (4 에이전트)

| 역할 | 담당 |
|------|------|
| `frontend-engineer` | Next.js 페이지·컴포넌트·차트·상태관리 |
| `backend-engineer` | FastAPI 라우트·LangGraph 노드·DB |
| `analyzer-designer` | Router/Analyzer 프롬프트·품질 게이트 설계 |
| `integration-qa` | E2E·계약 테스트·배포·데모 리허설 |

---

## 자연어 Copilot

헤더 커맨드바에 자연어를 입력하면 Router가 멀티스텝 에이전트 플랜을 수립해 기존 Analyzer에
신규 서브-에이전트(comparison/simulator/news-rag)를 체인 실행하고, 결과를 SSE 스트리밍으로
progressive하게 렌더합니다.

**주요 기능:**
- 단일 턴: `"TSLA vs NVDA 비교"` → comparison_table + chart 카드
- follow-up: `"그럼 엔비디아 -30% 시 내 포트폴리오?"` → simulator_result (세션 메모리 carry-over)
- news-rag: 뉴스/공시 pgvector 검색 + Claude citations 인용 강제
- 3단 게이트: 서브-스텝 레벨 + 최종 통합 레벨 양쪽 적용

**스크린샷:**

| 화면 | 미리보기 |
|------|---------|
| Copilot 쿼리 입력 | `docs/screenshots/copilot-query.png` |
| 최종 카드 렌더 | `docs/screenshots/copilot-final-card.png` |

- Playwright E2E: `npm run test:e2e` (3종: single-turn / follow-up / degraded)
- 골든 샘플 10건: `backend/tests/golden/samples/copilot/`
- 데모 스크립트: [demo-rehearsal-2026-04-22.md](docs/qa/demo-rehearsal-2026-04-22.md)

**stub 모드 실행 (API 키 불필요):**
```bash
# NEXT_PUBLIC_COPILOT_MOCK=1 환경에서 MSW SSE mock 사용
NEXT_PUBLIC_COPILOT_MOCK=1 npm run dev  # FE
# 또는 make copilot-demo (docker compose + stub mode)
```

---

## Copilot (자연어 질의)

> 상세 내용은 위 "자연어 Copilot" 섹션 참조.

---

## ADR (아키텍처 결정 로그)

- [0001 — 기술 스택 선택](docs/adr/0001-stack-selection.md)
- [0007 — 포트폴리오 컨텍스트 주입](docs/adr/0007-portfolio-context-injection.md)
- [0008 — 리밸런싱 제안 설계](docs/adr/0008-rebalance-proposal.md)
- [0011 — Copilot SSE + 멀티스텝 오케스트레이션](docs/adr/0011-copilot-sse-and-multistep-orchestration.md)
- [0012 — 뉴스 RAG pgvector 벡터 스토어](docs/adr/0012-news-rag-vector-store.md)

---

## 배포 런북

- [Fly.io BE 배포](docs/ops/deploy-runbook.md)
- [Neon Postgres 운영](docs/ops/neon-runbook.md)
