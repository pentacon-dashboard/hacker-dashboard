# Planner Prompt

Convert a user request into a bounded implementation plan for `hacker-dashboard`.

Read `AGENTS.md`, `.codex/project.md`, `.codex/instructions/common.md`, and the relevant area instruction before planning. For investment analysis, upload, portfolio, reporting, or dashboard work, also account for `$investment-dashboard`.

## Required Plan Shape

Always identify:

1. affected area: frontend, backend, analyzer, QA, docs, deploy, or skill;
2. source files likely to change;
3. data assumptions: CSV schema, broker mapping confidence, client id, holdings count, market, currency, and fixture/API source;
4. deterministic metric assumptions and where those metrics are computed;
5. LLM narrative boundaries and evidence requirements;
6. API contract impact, including whether `make openapi` is required;
7. validation commands, starting with the narrowest meaningful check;
8. demo/submission impact.

## Project Gates

Include these when relevant:

- Router/Analyzer changes require deterministic routing reasons, gate metadata, and focused golden/unit tests.
- Prompt, Analyzer output, or report contract changes require golden sample updates.
- Portfolio API shape changes require `make openapi` plus aligned `shared/openapi.json` and `shared/types/api.ts`.
- Customer-book, upload/import, portfolio API, Docker/Postgres, or browser-smoke work requires the demo preflight and browser verification of `/` plus linked `/clients/<client_id>` routes after data loads.
- Frontend-only customer/portfolio MSW checks can verify the UI shell, but they do not prove backend or demo readiness.

Keep the plan short enough to execute immediately. If the request spans independent subsystems, split it into separate work slices with clear write scopes.
