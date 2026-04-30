# Mock Boundary Reference

Use this reference whenever a harness run touches frontend mocks, demo data,
Copilot, market data, news, watchlist, Docker env, or API wiring.

## Principle

Customer demo data may be mocked. Live market/news/Copilot integrations must
remain real by default.

## Hard Rules

- Browser MSW may register only customer/portfolio demo handlers in normal app runtime.
- Do not register global browser handlers for market indices, symbol search, quotes, news, watchlist, notifications, settings, upload, or Copilot.
- Do not enable app-level mocks from `NEXT_PUBLIC_COPILOT_MOCK` or `COPILOT_MOCK`.
- Copilot query routes must proxy to backend `/copilot/query`; they must not return local mock SSE streams.
- Copilot news/RAG code must use `app.services.news.search.search_news()` so configured live news providers are attempted first.
- Realtime quotes/WebSocket code must not be disabled by customer demo mock flags.
- Docker Compose backend services must receive the repo env files needed for real API integrations, without printing secret values in logs or docs.

## Required Boundary Checks

When touched files include MSW, Copilot, realtime quotes, live news, or Docker env,
run the relevant guard tests:

- `cd frontend && npx vitest run tests/harness/mock-boundary.test.ts`
- `cd backend && uv run pytest tests/harness/test_live_api_boundaries.py -q`

Also run normal type/lint checks for the edited surface.

## Review Questions

- Could a customer-only mock flag make stock prices, news, watchlist, or Copilot fake?
- Does the browser worker import any non-customer mock handler?
- Does Copilot have any route-local mock stream path?
- Does live news retrieval still pass through the service that checks configured providers first?
- Are Docker env files wired so API keys reach backend containers without being committed or printed?
