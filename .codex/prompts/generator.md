# Generator Prompt

Implement the planned change using existing project patterns.

Before editing, read `AGENTS.md`, `.codex/project.md`, `.codex/instructions/common.md`, and the relevant area instruction. For investment analysis, reporting, upload, portfolio, or dashboard work, follow `$investment-dashboard`.

## Implementation Rules

- Prefer focused edits and preserve unrelated dirty worktree changes.
- Keep deterministic metric code separate from LLM narrative.
- LLM output may explain already-computed facts, but must not invent numbers, tickers, causal claims, actions, or personalized investment advice.
- Preserve OpenAPI contracts unless the task intentionally changes API shape.
- If API shape changes, run `make openapi` and keep `shared/openapi.json` plus `shared/types/api.ts` aligned.
- If Router, Analyzer, prompt, gate, or report output contracts change, update golden samples/tests.
- Keep browser MSW scoped to customer/portfolio demo data only; do not add global app mocks for market data, symbol search, quotes, news, watchlist, notifications, settings, uploads, realtime, or Copilot.
- Do not reintroduce `NEXT_PUBLIC_COPILOT_MOCK`, `COPILOT_MOCK`, `mock_scenario`, or route-level mock SSE responses into normal app code.
- Do not modify `.claude/`, `.env*`, secrets, local screenshots, Playwright reports, caches, or harness workspaces.

## Verification

- Run the narrowest meaningful test first.
- For frontend typed UI/API changes, run `cd frontend && npm run typecheck`.
- For backend service/API changes, run focused `uv run pytest` targets.
- For customer-book, upload/import, portfolio API, Docker/Postgres, demo seed, or routed browser-smoke work, run the harness demo preflight and verify `/` plus linked `/clients/<client_id>` routes after data loads.
- Report checks not run and why.
