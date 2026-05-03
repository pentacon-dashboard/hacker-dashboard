# Demo Runtime Preflight

Use this reference whenever a harness run touches customer books, upload/import,
portfolio APIs, Docker/Postgres setup, demo seeds, or browser smoke evidence.

## Principle

Do not treat a rendered shell, green API badge, or homepage load as demo-ready.
The backend must be connected to the same database that contains the expected
demo client ledgers, and browser evidence must wait for loaded data, not the
initial skeleton.

## Required Checks

Before claiming a local demo is healthy, run the API preflight from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1
```

Use environment overrides only when the app is intentionally running elsewhere:

```powershell
$env:HARNESS_API_BASE = "http://127.0.0.1:8000"
$env:HARNESS_APP_BASE = "http://127.0.0.1:3000"
powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1
```

The script must fail if:

- `/health` does not report `services.db=ok`;
- `/portfolio/clients` omits any required demo client;
- any required demo client has `holdings_count < 1`;
- any required demo client has `total_value_krw <= 0`;
- the frontend URL is unreachable.

Default required clients are `client-001`, `client-002`, and `client-003`.
Pass `-RequiredClients` only when the sprint contract explicitly narrows the demo
surface.

## Docker And Database Rules

- Verify the backend `DATABASE_URL` points at the same Postgres instance exposed by Docker.
- Run migrations against that same database before browser smoke.
- If `/health` is degraded because `db` is unreachable, classify the issue as runtime infrastructure, not missing customer data.
- If `/health` is ok but a linked client summary is empty, classify the issue as missing ledger seed/import data.
- Do not print real API keys, database passwords, or `.env` contents in harness artifacts.

## Browser Smoke Rules

When using browser-use or Playwright for demo routes:

- Visit `/` and verify the customer list includes every required demo client.
- Visit each linked client route used by the demo, especially `/clients/client-003`.
- Wait until data-specific UI appears; do not stop at the first skeleton screenshot.
- For `/clients/<client_id>`, verify the heading uses the resolved client name, KPI cards render, holdings count is nonzero, and at least one expected holding row appears.
- Record console error count. A zero console error count is necessary but not sufficient.

## Failure Classification

Use these labels in work, review, and summary artifacts:

- `db_unreachable`: `/health` reports DB not ok or portfolio APIs return 500 from DB connection errors.
- `ledger_missing`: DB is ok, but required client rows or holdings are missing.
- `frontend_loading_stall`: API data exists, but the browser remains in skeleton/loading state after a targeted wait.
- `frontend_hidden_error`: API or query failure is not surfaced as an actionable error state.

## Review Gate

A harness review must block demo readiness when:

- the preflight script was not run for customer-book, upload, portfolio, or Docker work;
- browser evidence covers only `/` and not the linked client detail route;
- the checked client detail route has zero holdings while the demo links to it;
- a screenshot shows skeleton or empty state but is recorded as a pass.
