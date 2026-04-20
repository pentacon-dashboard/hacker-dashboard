# 금융 대시보드 (hacker-dashboard)

## 제품 개요

임의 투자 데이터 스키마에서 **자동으로 분석 뷰를 생성**하는 범용 금융 대시보드. 공모전 MVP 겸 포트폴리오 레퍼런스 프로젝트.

**핵심 아키텍처**

- **Router (Meta Agent)**: 입력 데이터/질의를 분석해 적절한 **자산군 Analyzer**를 동적 선택
- **Analyzers (Sub Agents)**: 주식·코인·환율·매크로 등 자산군별 분석 체인 (LangGraph 서브그래프)
- **3단 품질 게이트**:
  1. 스키마/타입 검증 (Zod / Pydantic)
  2. 도메인 sanity check (가격 범위·시간 정합성)
  3. LLM self-critique + 근거 인용 검증

## 기술 스택

| 계층 | 기술 |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind, shadcn/ui, TradingView Lightweight Charts |
| Backend | FastAPI, LangGraph, Pydantic v2, Python 3.12 |
| Data | Postgres(Neon) 또는 Supabase, Redis 캐시 |
| LLM | Claude Sonnet 4.6 (기본), Opus 4.7 (고난도 분석) |
| Infra | Docker Compose, Vercel(FE) + Fly.io/Render(BE) |

## 디렉토리 구조

```
hacker-dashboard/
├── frontend/          # Next.js 15 앱
├── backend/           # FastAPI + LangGraph
├── shared/            # 공유 스키마(OpenAPI → TS 타입 생성)
├── docker-compose.yml
└── .claude/           # 팀 규약·에이전트·스킬
```

경로별 세부 규칙은 `.claude/rules/` 가 자동으로 주입합니다.

## Agent Teams 4인 병렬 개발

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 환경에서 다음 4명이 병렬로 작업합니다. 각 에이전트는 독립 컨텍스트를 갖고, 공유 태스크 리스트로 조율됩니다.

| 역할 | 담당 |
|---|---|
| `frontend-engineer` | Next.js 페이지·컴포넌트·차트·상태관리 |
| `backend-engineer` | FastAPI 라우트·LangGraph 노드·DB |
| `analyzer-designer` | Router/Analyzer 프롬프트·품질 게이트 설계 |
| `integration-qa` | E2E·계약 테스트·배포·데모 리허설 |

에이전트 정의는 `.claude/agents/*.md`.

## 공통 규약 (모든 역할)

- **언어:** 코드·식별자는 영어, 커밋 메시지·PR 본문·주석의 WHY는 한국어 허용
- **커밋:** Conventional Commits (`feat:`, `fix:`, `chore:` …). 한 커밋 = 한 논리 단위
- **브랜치:** `main` 보호. 역할별 `feat/fe-*`, `feat/be-*`, `feat/agent-*`, `feat/qa-*`
- **PR:** 반드시 최소 1인 리뷰 + CI 통과. Draft 상태에서도 상대 역할이 API 계약 확인 가능해야 함
- **타입 우선:** 런타임 검증 전 컴파일 타입으로 잡을 수 있는 건 타입으로 잡기
- **계약 기반 통합:** FE ↔ BE 경계는 OpenAPI 스키마가 단일 진실. `shared/` 에서 TS 타입 자동 생성
- **비밀·키:** `.env*` 절대 커밋 금지. Vercel/Fly dashboard 에 주입
- **테스트:** 도메인 로직 단위 테스트 필수. LLM 체인은 골든 샘플 기반 회귀 테스트
- **스타일:** 포매터·린터에 맡긴다 (prettier + eslint, ruff + black). 수동 정렬 금지

## 결정 로그 (ADR)

아키텍처 수준의 결정은 `docs/adr/NNNN-title.md` 로 남긴다. 제목 · 맥락 · 결정 · 결과.

## 공모전 심사 기준 정렬

1. **기술적 깊이** — Router/Analyzer 다이어그램 + 품질 게이트 설명
2. **데모 임팩트** — 임의 CSV 업로드 → 5초 내 자동 대시보드
3. **완성도** — 로딩/에러/빈 상태, 반응형, 다크모드, Lighthouse 90+

## 금지 사항

- CLAUDE.md / `.claude/rules/*` 를 개별 역할이 단독 수정 금지 → 팀 합의 후 PR
- 본 저장소에 실 거래 API 키·개인 포트폴리오 값 커밋 금지 (데모용 고정 샘플만)
- LLM 응답을 검증 없이 UI 로 직결 금지 → 반드시 3단 게이트 통과
