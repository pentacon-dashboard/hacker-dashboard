# Harness Run Summary - 20260504-005400-demo-preflight-hardening

## Request

Prevent a repeat of the Docker/Postgres and missing customer-ledger issue by
hardening harness, skill, and QA instructions.

## Changes

- Added a deterministic demo runtime preflight script for API health, required
  client presence, non-empty client summaries, and frontend reachability.
- Added a harness reference that classifies failures as `db_unreachable`,
  `ledger_missing`, `frontend_loading_stall`, or `frontend_hidden_error`.
- Updated harness contracts, artifacts, and review rules so customer-book demo
  readiness requires API preflight plus loaded client-detail browser evidence.
- Updated investment-dashboard and project QA instructions so linked demo client
  routes cannot be treated as passing when their ledger is empty.

## Checks

| Command | Result |
|---|---|
| `powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1` | pass |
| `powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1 -RequiredClients client-does-not-exist -SkipFrontend` | expected failure |
| `python C:\Users\ehgus\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\ehgus\hacker-dashboard\.agents\skills\investment-dashboard` | pass |
| `$env:PYTHONUTF8='1'; python C:\Users\ehgus\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\ehgus\hacker-dashboard\.agents\skills\harness-run` | pass |

## Checks Not Run

- Full backend/frontend suites were not run because this change is limited to
  harness/skill documentation and a standalone preflight script.
- Browser smoke was not rerun for this hardening summary; the preflight script
  now makes the API/data prerequisite explicit before future browser smoke.

## Residual Risks

- The preflight script validates API/data readiness and frontend reachability,
  but visual confirmation still requires browser-use or Playwright as documented
  in `references/demo-preflight.md`.
