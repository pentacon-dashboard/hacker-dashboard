# Codex Project Instructions

## Scope

This file is project-scoped for `C:\Users\ehgus\hacker-dashboard`. It replaces the old Claude-centered workflow for Codex runs in this repository. Do not edit user-level Codex files such as `~/.codex/*` for this project.

## Primary Skill

Use `$investment-dashboard` for work involving:

- arbitrary investment CSV upload and schema detection;
- broker CSV adapter rules, field mapping confidence, or PB confirmation flows;
- Router or Analyzer behavior;
- client portfolio normalization, holdings, allocation, concentration, rebalance, or risk metrics;
- dashboard charts, insight cards, evidence panels, gate badges, or client briefing reports;
- competition-facing `Skills.md` documentation.

The Codex-readable skill lives at `.agents/skills/investment-dashboard/SKILL.md`. The judge-facing entrypoint is `Skills.md`, with the expanded specification at `.codex/competition/Skills.md`.

## Codex Folder Semantics

- `AGENTS.md`: official project instruction entrypoint. Keep durable project rules here.
- `.codex/config.toml`: project-scoped Codex configuration for trusted runs.
- `.codex/agents/*.toml`: project-scoped custom agents. Each file defines one spawned agent role.
- `.codex/rules/*.rules`: project-scoped command approval policy loaded from the active `.codex/` layer.
- `.agents/skills/<name>/SKILL.md`: repository skills discovered by Codex from the working directory up to the repository root.
- `.codex/instructions/*.md`: project-local support instructions referenced by `AGENTS.md`, skills, or custom agents.
- `.codex/prompts/`: reusable project prompts. Load them only when a workflow references them.
- `.codex/competition/`: competition-facing specs and submission support docs.

## Project Shape

- Frontend: `frontend/` with Next.js App Router, React 19, TypeScript, Tailwind, shadcn/ui, Recharts, lightweight-charts, TanStack Query, Zustand.
- Backend: `backend/` with FastAPI, Python 3.12, Pydantic v2, Router/Analyzer/Gates, broker normalization, portfolio/report services, Copilot/Search routes, Postgres, Redis.
- Shared contract: `shared/openapi.json`, `shared/types/api.ts`.
- Demo and golden data: `demo/seeds/`, `frontend/public/demo/`, `backend/tests/golden/samples/`.
- Submission docs: `submission/`, `docs/adr/`, `docs/agents/`, `docs/harness-runs/`.

## Non-Negotiable Analysis Rules

- Deterministic code calculates metrics. LLMs explain already-calculated metrics.
- Router heuristics based on symbols, markets, and columns win over LLM routing when evidence is clear.
- Every numeric insight must cite input rows, deterministic metrics, API data, or fixture data.
- Never present guaranteed returns, certain price direction, or unsupported personalized investment advice.
- Schema, domain, and critique gates must protect LLM-facing analysis before UI rendering.
- Rebalance actions must remain deterministic and must survive LLM analysis failure.
- PB/client briefing reports must cite rows, deterministic metrics, API data, or fixtures at section level.
- If report evidence, source data, or gate verification is insufficient, return a degraded or `insufficient_data` state instead of filling gaps.

## Development Rules

- Keep changes scoped to the requested feature and existing architecture.
- Apply `.codex/instructions/common.md` for all work; apply the area-specific instruction file before frontend, backend, analyzer, or QA work.
- Do not extend `.claude/`; it is legacy context only.
- If backend API shape changes, run `make openapi` and commit generated `shared/` changes.
- If Analyzer prompts or output contracts change, update golden samples/tests.
- Do not commit `.env*`, secrets, local screenshots, Playwright reports, caches, or harness workspaces.

## Live API and Mock Boundaries

- Browser MSW may only be used for customer/portfolio demo data unless the user explicitly asks to mock another domain.
- Do not let customer demo flags such as `NEXT_PUBLIC_CLIENT_MOCK` or `NEXT_PUBLIC_USE_MSW_WORKER` intercept market data, symbol search, quotes, news, watchlist, notifications, settings, uploads, or Copilot.
- Copilot must use the real frontend proxy and backend route by default. Do not reintroduce `NEXT_PUBLIC_COPILOT_MOCK`, `COPILOT_MOCK`, `mock_scenario`, or route-level mock SSE responses into normal app code.
- Realtime quote/WebSocket behavior must not be disabled by customer demo mock flags. Use an explicit realtime flag only when a test or user request requires it.
- Docker Compose must pass repo-local API key env files into backend without printing secret values, and live news/Copilot checks must verify through backend endpoints rather than browser mocks.
- Add or update boundary tests whenever changing `frontend/tests/mocks/browser.ts`, `frontend/components/providers/msw-provider.tsx`, `frontend/app/api/copilot/query/route.ts`, realtime ticker code, or Copilot news retrieval.

## Verification

- Backend focused: `cd backend && uv run pytest tests/golden tests/unit/agents tests/services -q`.
- Backend full: `cd backend && uv run pytest -q`.
- Frontend unit: `cd frontend && npm run test`.
- Frontend typecheck: `cd frontend && npm run typecheck`.
- Frontend lint: `cd frontend && npm run lint`.
- E2E smoke: `cd frontend && npx playwright test e2e/smoke.spec.ts --config=e2e/playwright.config.ts`.
- Full local gate: `make ci-local`.

When finalizing work, report changed files, checks run, and checks not run.
