# Frontend Instructions

## Stack

- Next.js App Router, React, TypeScript, Tailwind, shadcn/ui.
- Server state: TanStack Query.
- UI state: Zustand.
- Charts: lightweight-charts for price charts, Recharts for allocation and summary charts.

## Dashboard UX

- First useful view after upload must show KPI, primary chart, and first insight.
- Always include loading, empty, error, and degraded states.
- Show Router reason, gate status, evidence, and confidence for analysis outputs.
- Keep operational dashboard density; avoid marketing-style landing pages.

## Mock Boundaries

- Browser MSW is for customer/portfolio demo endpoints only. Do not register market, symbol, quote, news, watchlist, notifications, settings, upload, or Copilot handlers in the app-level browser worker.
- `NEXT_PUBLIC_COPILOT_MOCK` and `COPILOT_MOCK` are not valid app-runtime switches. Copilot should proxy to the backend by default.
- Do not disable realtime WebSocket quotes because a customer demo mock is enabled. Use `NEXT_PUBLIC_DISABLE_REALTIME_WS=1` only for an explicit realtime test scenario.
- If a route needs deterministic data for a test, keep that mock inside the test fixture or Playwright route, not the global app provider.
- Before finishing mock-related frontend work, run the mock boundary tests in `frontend/tests/harness/mock-boundary.test.ts`.

## Tests

- Run focused Vitest for changed components.
- Run `npm run typecheck` for typed API/UI changes.
- Use Playwright for routed visual workflows.
- For customer-book demo routes, verify loaded data in `/` and linked `/clients/<client_id>` routes. Do not accept a skeleton, hidden error, or empty workspace as a passing smoke when the API has holdings.

## Browser Verification Profiles

- Frontend-only visual check: run the app with customer/portfolio demo MSW only. This can confirm shell, layout, and routed UI, but it does not prove backend health.
- Full runtime check: run backend, database, and frontend together; verify `/health` has `services.db=ok`, `/` loads customer KPI/list content, and linked `/clients/<client_id>` routes show non-empty holdings.
- Treat an `API 오류` or long `API 확인 중` header as a runtime signal to investigate unless the task explicitly requested frontend-only mock verification.
