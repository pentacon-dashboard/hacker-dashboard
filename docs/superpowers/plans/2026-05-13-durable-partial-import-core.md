# Durable Partial Import Core Plan

Date: 2026-05-13
Status: Draft for subagent-driven execution

## Goal

Implement milestone 1 from ADR 0015: durable partial CSV import without adding the AI mapper yet. The deterministic upload/import path must support optional cost basis, partial import status, and durable row-level audit records while preserving the existing deterministic fallback flow.

## Constraints

- Do not touch unrelated frontend dashboard/chart files already modified in the worktree.
- Follow `CONTEXT.md`, ADR 0015, and `.agents/skills/investment-dashboard` rules.
- Deterministic code decides DB writes. No AI calls in milestone 1.
- Missing cost basis must never be converted to zero.
- If backend API shapes change, run `make openapi` and update `shared/openapi.json` plus `shared/types/api.ts`.
- Preserve batch replacement behavior from ADR 0014.

## Task 1: Durable Schema And Contract Foundation

Add the durable schema foundation required by partial import, without changing row classification behavior yet.

Requirements:

- Add a new Alembic migration after `009_client_registry.py`.
- Make `holdings.avg_cost` nullable.
- Add `holdings.cost_basis_status` with accepted values represented as strings: `provided`, `missing`, `derived`, `needs_review`. Existing rows should default to `provided`.
- Add a durable import row ledger table, named `portfolio_import_rows`, linked to an import batch by `import_batch_key`.
- The row ledger must store at least: `id`, `user_id`, `client_id`, `import_batch_key`, `source_row`, `row_status`, `raw_row_json`, `normalized_payload_json`, `reason_codes`, `linked_holding_id`, `created_at`.
- Add indexes for `import_batch_key`, `client_id`, and `row_status` where locally consistent with existing migration style.
- Update SQLAlchemy models in `backend/app/db/models.py`.
- Update test metadata in `backend/tests/conftest.py`.
- Update Pydantic schemas so upload/import status can include `partial_imported`; `NormalizedCsvHolding` can expose `cost_basis_status`; `HoldingResponse` and `HoldingDetail` can represent missing `avg_cost`.
- Keep existing tests passing as much as possible; do not implement partial import logic in this task.

Acceptance checks:

- Focused backend schema/unit tests import successfully.
- Existing upload service tests still run to the point of behavior assertions; expected failures should only be from behavior not yet implemented in later tasks.
- Migration downgrade reverses added schema.

Owned files:

- `backend/alembic/versions/*`
- `backend/app/db/models.py`
- `backend/app/schemas/upload.py`
- `backend/app/schemas/portfolio.py`
- `backend/tests/conftest.py`

## Task 2: Row-Level Deterministic Intake Result

Introduce deterministic row-level classification in upload services.

Requirements:

- Extend normalization results to include row ledgers for imported, recoverable, quarantined, and garbage rows.
- Classify blank rows, subtotal/total rows, and repeated headers as garbage.
- Allow rows with symbol, quantity, and market but missing avg cost to normalize as positions with `cost_basis_status = missing`.
- Keep rows with invalid quantity, unsupported currency, contradictory market/currency, or unresolved symbol as quarantined or recoverable rather than failing unrelated valid rows.
- Preserve original source row indexes and source columns.
- Add unit tests that demonstrate 98 valid rows + 2 invalid rows can yield imported rows plus quarantined row evidence.

Owned files:

- `backend/app/services/upload.py`
- `backend/app/schemas/upload.py`
- `backend/tests/unit/test_upload_service.py`

## Task 3: Partial Import Persistence

Persist valid rows and row-ledger entries during `/upload/import`.

Requirements:

- Persist valid imported rows to `holdings`, including nullable avg cost and `cost_basis_status`.
- Persist every classified source row into `portfolio_import_rows`.
- Return `partial_imported` when at least one row imports and at least one row is recoverable, quarantined, or garbage.
- Preserve ADR 0014 batch replacement semantics for rows and holdings tied to the same `import_batch_key`.
- Ensure `portfolio_import_batches.status` records the new status vocabulary.
- Add backend tests for imported, partial_imported, and insufficient_data outcomes.

Owned files:

- `backend/app/services/upload_import.py`
- `backend/app/schemas/upload.py`
- `backend/tests/unit/test_upload_service.py`
- related API tests under `backend/tests/api/`

## Task 4: Portfolio Metrics Degrade Missing Cost Basis

Make portfolio summary safe for positions with missing cost basis.

Requirements:

- `compute_summary` must include position market value in total value and allocation even when avg cost is missing.
- Cost-basis-dependent values must degrade rather than inventing cost: total cost, PnL, return, win rate, dimension PnL, and holding detail PnL must not use zero as fake cost.
- Add explicit output evidence/status fields if needed; otherwise use nullable/empty values consistently and document behavior in tests.
- Rebalance should continue to use current value and reference price where possible, but explanations that depend on PnL/cost basis must degrade.

Owned files:

- `backend/app/services/portfolio.py`
- `backend/app/services/portfolio_service.py`
- `backend/app/schemas/portfolio.py`
- focused portfolio tests

## Task 5: Contract Regeneration And Frontend Review Surface

Reflect new partial-import contract in frontend and shared types.

Requirements:

- Run `make openapi` if backend API shape changed.
- Update frontend upload-import types and handling for `partial_imported`.
- Show imported, review, quarantine, and garbage counts in upload validation/import result surfaces using existing upload UI patterns.
- Do not build the full row-ledger detail page yet; only expose summary counts and warnings needed for milestone 1.
- Keep existing upload page tests updated.

Owned files:

- `shared/openapi.json`
- `shared/types/api.ts`
- `frontend/lib/portfolio/upload-import.ts`
- `frontend/app/upload/page.tsx`
- `frontend/app/upload/page.test.tsx`
- `frontend/components/upload/*` only if needed
