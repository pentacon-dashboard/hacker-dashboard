---
name: investment-dashboard
description: Use for hacker-dashboard PB/WM investment analysis work, including arbitrary broker CSV schema detection, Router/Analyzer logic, client portfolio normalization, deterministic financial metrics, rebalance analysis, evidence-backed insight generation, validation gates, dashboard visualization, and client briefing report documentation.
---

# Investment Dashboard

Use this skill when working on investment data analysis, PB/WM reporting, or dashboard behavior in `C:\Users\ehgus\hacker-dashboard`.

## Workflow

1. Read `.codex/project.md` for project context when needed.
2. Read `.codex/instructions/common.md` and the relevant work-area instruction file when editing code or docs.
3. Read `references/analysis-rules.md` for Router, metric, asset-class, and rebalance behavior.
4. Read `references/broker-csv-adapter-rules.md` when upload/schema detection touches broker or exchange CSV files.
5. Read `references/client-normalization-rules.md` when work touches customer, account, market, currency, or multi-account consolidation.
6. Read `references/quant-metric-rules.md` before changing metric, risk, allocation, or rebalance calculations.
7. Read `references/evidence-compliance-rules.md` before generating or validating AI narrative, report text, evidence panels, or gate badges.
8. Read `references/report-rules.md` when implementing client briefing reports, report export, or PB-facing summary scripts.
9. Read `references/visualization-rules.md` for dashboard layout and chart selection.
10. Read `references/insight-rules.md` for narrative, confidence, and forbidden claims.
11. Read `references/validation-rules.md` before finalizing behavior.
12. Keep `Skills.md`, `.codex/competition/Skills.md`, and these reference files aligned when the analysis rule system changes.
13. When customer-book, upload/import, portfolio API, Docker/Postgres, demo seed, or browser-smoke behavior is in scope, also follow `$harness-run` `references/demo-preflight.md`.

## Core Behavior

- Normalize data before routing it.
- Classify data before analyzing it.
- Compute metrics deterministically before generating narrative.
- Attach evidence to every numeric or factual claim.
- Use schema, domain, evidence, and critique gates before rendering LLM narrative or report text as a normal result.
- Keep rebalance actions deterministic and available even when LLM analysis fails.
- Degrade gracefully when data is incomplete, mapping confidence is low, evidence is missing, or an LLM is unavailable.

## Implementation Rules

- Backend analysis belongs in `backend/app/agents/` and `backend/app/services/`.
- Broker normalization and report generation belong in `backend/app/services/` with API surfaces in `backend/app/api/`.
- Frontend visualization belongs in `frontend/components/dashboard/`, `frontend/components/portfolio/`, `frontend/components/analyze/`, `frontend/components/reports/`, or related route components.
- API contract changes require `make openapi`.
- Prompt, Analyzer, gate, or report contract changes require golden sample updates.
- Do not put customer-specific assumptions, risk profiles, or investment objectives into output unless they exist in input or approved fixtures.
- Do not link to a demo client workspace unless that client has ledger data or the route intentionally demonstrates an empty state.

## Verification

Run the narrowest meaningful check first:

- Router/Analyzer: `cd backend && uv run pytest tests/golden tests/unit/agents -q`
- Services: `cd backend && uv run pytest tests/services -q`
- Reports or output contracts: update golden samples, then run related backend tests.
- Frontend component: `cd frontend && npm run test`
- Type/API changes: `cd frontend && npm run typecheck`
- Routed UX and local browser smoke: use `browser-use` first.
- Automated routed regression: use Playwright only when CI-style E2E evidence is needed or explicitly requested.
- Client-book demo runtime: `powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1`, then verify `/` and each linked `/clients/<client_id>` route after data has loaded.
