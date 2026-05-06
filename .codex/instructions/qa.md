# QA Instructions

## Required Coverage Areas

- CSV upload and schema validation.
- Router classification and reason display.
- Analyzer output structure and gate metadata.
- Portfolio context opt-in and graceful degradation.
- Customer-book runtime integrity: backend DB health, required demo clients, non-empty client summaries, and loaded client detail routes.
- Rebalance deterministic actions with LLM failure fallback.
- Dashboard loading, empty, error, and degraded states.

## Evidence

Use these evidence sources:

- `backend/tests/golden/samples/`.
- `docs/harness-runs/*/summary.md`.
- `submission/test-coverage.md`.
- Playwright screenshots only when they are intentionally captured for review.
- Harness demo preflight output from `.agents/skills/harness-run/scripts/check-demo-preflight.ps1`.

## Reporting

Lead with failing behavior, regression risk, and missing tests. Keep summaries secondary.

## Demo Readiness Gate

For customer-book, upload/import, portfolio API, Docker/Postgres, or browser-smoke work:

- Run `powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1`.
- Verify `/` and each linked `/clients/<client_id>` route in browser-use or Playwright after data has loaded.
- Do not count a skeleton, empty workspace, or green API badge alone as a passing routed smoke.
- Do not count frontend-only MSW customer data as backend/demo readiness; it is useful only for UI shell verification.
- Classify failures as `db_unreachable`, `ledger_missing`, `frontend_loading_stall`, or `frontend_hidden_error`.
