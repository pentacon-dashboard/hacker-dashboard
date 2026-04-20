# ADR 0001: 기술 스택 확정

**날짜:** 2026-04-19
**상태:** 확정(Accepted)
**결정자:** 전체 팀 (frontend-engineer / backend-engineer / analyzer-designer / integration-qa)

---

## 맥락 (Context)

임의 투자 데이터 스키마를 업로드하면 자동으로 분석 대시보드를 생성하는 MVP를 공모전 기간(4주) 안에 완성해야 한다. 요구사항은 다음과 같다.

- **데모 임팩트**: CSV 업로드 후 5초 내에 차트·분석 결과가 보여야 한다.
- **기술적 깊이**: LLM 기반 Router → 자산군별 Analyzer 구조 + 3단 품질 게이트를 심사 자료로 제시.
- **완성도**: 반응형, 다크모드, Lighthouse 90+, 로딩/에러/빈 상태 처리.
- **팀 규모**: 4인 병렬 개발, 역할별 독립 컨텍스트.

공모전 마감 압박과 포트폴리오 레퍼런스라는 이중 목적을 동시에 충족해야 한다.

---

## 결정 (Decision)

| 계층 | 선택 기술 | 버전 |
|---|---|---|
| 프론트엔드 | Next.js (App Router) + React + TypeScript + Tailwind + shadcn/ui | 15 / 19 / 5 |
| 차트 | TradingView Lightweight Charts (가격·캔들) + Recharts (집계) | 4.x / 2.x |
| 상태 관리 | TanStack Query (서버 상태) + Zustand (UI 상태) | 5.x / 5.x |
| 백엔드 | FastAPI + Pydantic v2 | 0.115 / 2.7 |
| 오케스트레이션 | LangGraph (Router/Analyzer 서브그래프) | 0.2+ |
| LLM | Anthropic Claude Sonnet 4.6 (기본) / Opus 4.7 (고난도) | API |
| 데이터베이스 | Neon (Postgres 16, 서버리스) | 16 |
| 캐시 | Redis 7 | 7-alpine |
| 배포 FE | Vercel | — |
| 배포 BE | Fly.io 또는 Render | — |
| 컨테이너 | Docker Compose (로컬) + 멀티스테이지 빌드 | 3.9 |
| CI | GitHub Actions — lint/type/test/build/schemathesis | — |

---

## 근거 (Rationale)

**Next.js 15 App Router + React 19**
Server Components 로 초기 렌더를 서버에서 처리해 Lighthouse 점수를 확보한다. streaming SSR 로 LLM 응답이 느릴 때도 사용자에게 즉시 스켈레톤을 노출할 수 있다.

**FastAPI + Pydantic v2**
비동기 I/O 네이티브로 LLM API 대기시간을 차단 없이 처리. Pydantic 모델이 OpenAPI 스키마로 자동 변환되어 FE 타입 생성(`openapi-typescript`) 파이프라인과 직결된다.

**LangGraph**
Router(Meta Agent) → Analyzer(Sub Agent) 패턴을 서브그래프로 명시적으로 표현하고 디버그 추적(LangSmith 선택적)이 가능하다. LangChain Expression Language 보다 상태 전이가 명확해 3단 품질 게이트 구현에 유리하다.

**Anthropic Claude**
팀이 Anthropic API 에 익숙하고, 프롬프트 캐시(`cache_control`) 로 반복 호출 비용을 절감할 수 있다. Sonnet 4.6 을 기본으로 사용하고 복잡한 분석은 Opus 4.7 로 라우팅.

**Neon + Vercel + Fly.io**
각각 무료 티어로 공모전 기간 비용 없이 운영 가능. Neon 은 branch per PR 기능으로 DB 격리 테스트 환경을 쉽게 구성할 수 있다.

---

## 결과 (Consequences)

**긍정적:**
- FE/BE 타입 계약이 `shared/openapi.json` 단일 소스로 자동 유지된다.
- LangGraph 서브그래프 다이어그램이 심사 자료로 직접 활용된다.
- 서버리스 DB + Vercel 으로 콜드 스타트 이후 스케일 아웃 부담 없음.

**트레이드오프:**
- Next.js App Router + React 19 는 아직 생태계 일부가 불안정. `"use client"` 경계 설계를 초기에 확정해야 한다.
- LangGraph 학습 곡선 존재. 첫 주에 Router → StockAnalyzer 최소 경로부터 검증.
- Neon 무료 티어 연결 수 제한(10) — 커넥션 풀 설정 필요.

---

## 검토한 대안 (Alternatives Considered)

| 대안 | 기각 이유 |
|---|---|
| Node.js + LangChain.js 전체 스택 | Python 생태계(pandas, numpy) 를 버릴 경우 데이터 전처리 코드를 재작성해야 함. LangGraph Python 이 상태 관리 표현력이 더 높음 |
| tRPC (FE↔BE 타입 공유) | 백엔드가 Python FastAPI 이므로 tRPC 적용 불가. OpenAPI → TS 자동 생성으로 동등한 타입 안전성 확보 |
| Supabase (Postgres + Auth) | 기능은 충분하나 Neon 의 branch-per-PR 과 서버리스 스케일링이 MVP 에 더 적합. Auth 는 공모전 범위 밖 |
| Vercel AI SDK + OpenAI | Anthropic SDK 직접 사용이 프롬프트 캐시 제어 및 thinking 파라미터 활용에 더 유연 |
| Remix 또는 SvelteKit | React 생태계(shadcn/ui, TanStack Query) 재사용 가능성이 낮아 4주 일정에 부담 |
