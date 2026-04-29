# hacker-dashboard Codex Context

## Product Summary

`hacker-dashboard` is a PB/WM investment data workspace for the hackathon requirement: define reusable investment analysis rules in a Skills document and use vibe coding to build a data-driven dashboard that handles changing investment data structures.

The product accepts arbitrary CSV, broker account exports, or portfolio data, normalizes the input, classifies it through a Meta Router, computes deterministic investment metrics, validates insight quality, and renders dashboard views plus client briefing reports. When data or LLM output is incomplete, the product must show degraded or `insufficient_data` states instead of filling gaps.

## Architecture

1. Frontend upload, dashboard, portfolio, report, and copilot UI in `frontend/`.
2. FastAPI ingestion, upload, analyze, portfolio, report, market, watchlist, notifications, search, and copilot endpoints in `backend/app/api/`.
3. Router Meta Agent in `backend/app/agents/router.py`.
4. Asset-class analyzers in `backend/app/agents/analyzers/`.
5. Safety gates in `backend/app/agents/gates/`.
6. Deterministic broker normalization, portfolio, rebalance, and report services in `backend/app/services/`.
7. Market/news/search fixtures and optional external integrations behind services.
8. Shared OpenAPI contract in `shared/`.

## Codex Structure

- Use root `AGENTS.md` as the instruction entrypoint.
- Use `.codex/config.toml` for project-scoped Codex configuration.
- Use `.codex/agents/*.toml` for custom subagents.
- Use `.codex/rules/*.rules` for command approval policy.
- Use `.agents/skills/investment-dashboard/` for Codex skill discovery.
- Use root `Skills.md` as the judge-facing summary entrypoint.
- Use `.codex/competition/Skills.md` as the expanded competition specification.
- Treat `.claude/` as historical evidence only.

## Competition Focus

Emphasize these when making changes or writing submission material:

- arbitrary broker CSV and schema handling;
- field mapping confidence and PB confirmation flow;
- Router decision transparency;
- deterministic financial metrics;
- client portfolio normalization;
- visualization selection rules;
- insight and report generation rules;
- schema/domain/evidence/critique validation;
- Copilot and dashboard outputs that cite evidence instead of inventing facts;
- client briefing reports with section-level evidence;
- reproducible demo and tests.
