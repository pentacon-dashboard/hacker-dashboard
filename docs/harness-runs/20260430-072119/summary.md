# Harness Run Summary - 2026-04-30 07:21

## Request
Repeat the harness run until these QA findings are fixed:

- Rebalance fetch failure
- Client book/workspace Korean language gaps
- Calendar layout problem
- Duplicate key warning

## Outcome
Completed in `sprint-01` iteration 1.

## Fixed
- Rebalance proposal fetch now succeeds in browser/MSW flow and renders Korean proposal results.
- Client book and client workspace primary labels, risk labels, sector labels, AI insight badges, and close labels are Korean.
- Monthly return calendar labels are Korean, and the header date range picker now renders as a proper two-month grid.
- Duplicate React key warning in symbol news items is fixed with a composite key.
- Browser mock coverage now includes health, notifications, portfolio holdings, rebalance, and symbol-detail endpoints needed for clean console QA.

## Verification
- `cd frontend && npm run typecheck`
- `cd frontend && npm run lint`
- `cd frontend && npm run test -- --run`
- `cd frontend && npx playwright test e2e/dashboard.spec.ts e2e/portfolio.spec.ts --config=e2e/playwright.config.ts`
- Browser console checks on `/`, `/clients/client-002`, and `/symbol/yahoo/AAPL`: 0 errors, 0 warnings.
