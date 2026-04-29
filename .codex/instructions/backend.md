# Backend Instructions

## Stack

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, asyncpg, Redis.
- Package manager: `uv`.
- Router/Analyzer/Gate code lives under `backend/app/agents/`.
- Domain services live under `backend/app/services/`.

## API

- Public request/response models must be Pydantic models.
- API changes require `make openapi`.
- Keep frontend/backend contract in `shared/openapi.json` and `shared/types/api.ts`.

## Financial Logic

- Calculations must be deterministic and testable.
- LLM calls must receive computed metrics, not raw permission to invent metrics.
- Gate outputs must be surfaced in response metadata where the UI depends on them.

## Tests

- For Router/Analyzer changes, run focused golden and unit tests.
- For API changes, run related API tests and OpenAPI contract checks when feasible.
- For prompt changes, add or update golden samples.
