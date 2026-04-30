# Harness Run Summary - Mock Boundary Guardrails

## Request

Prevent a repeat of customer demo mocks leaking into live market data, news,
watchlist, realtime quotes, or Copilot.

## Changes

- Added live API/mock boundary rules to `AGENTS.md`.
- Added frontend-specific mock boundary rules to `.codex/instructions/frontend.md`.
- Added harness reference `.agents/skills/harness-run/references/mock-boundary.md`.
- Linked the new reference from `.agents/skills/harness-run/SKILL.md`.
- Added frontend boundary tests in `frontend/tests/harness/mock-boundary.test.ts`.
- Added backend boundary tests in `backend/tests/harness/test_live_api_boundaries.py`.

## Guardrails

- Browser MSW may only register customer/portfolio demo handlers.
- Copilot route-local mock SSE paths are prohibited in normal app code.
- Customer mock flags must not disable realtime quotes.
- Copilot news/RAG must call the live search service path first.
- Docker Compose must wire backend env files for real API integrations.

## Verification

- `cd frontend && npx vitest run tests/harness/mock-boundary.test.ts`
- `cd backend && uv run pytest tests/harness/test_live_api_boundaries.py -q`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run lint`
- `cd backend && uv run ruff check app/agents/analyzers/news_rag.py app/services/copilot/orchestrator.py tests/harness/test_live_api_boundaries.py`

All checks passed.

## Notes

The repository already had many unrelated modified files before this run. This
run only added guardrails and tests for the mock/live API boundary.
