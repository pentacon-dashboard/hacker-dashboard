# ADR 0015: AI-Assisted Partial Portfolio CSV Intake

**Status:** Accepted
**Date:** 2026-05-13

## Context

The product must import arbitrary PB/WM portfolio CSV files whose broker, exchange, language, column names, row order, and content quality vary. The current upload flow maps CSV columns into canonical holdings and imports only when required holding fields can be verified. That all-or-nothing behavior is too strict for real portfolio exports, where a file may contain valid positions, missing cost basis, repeated headers, subtotal rows, multiple clients, multiple accounts, and non-holding transaction or cash rows.

The project rules still require deterministic metrics and evidence-backed import behavior. AI may help interpret unfamiliar CSV structure, but it must not fabricate financial values, infer unsupported customer context, or directly write client portfolio data.

## Decision

We will implement AI-assisted CSV intake as a semantic mapping and row-classification aid, not as the import authority.

The AI semantic mapper will inspect only sanitized CSV structure: original column names, normalized column names, a small row sample, value-pattern summaries, and redacted examples. It must return strict structured mapping output, including CSV kind, proposed column mappings, row classification rules, evidence, confidence, and risk flags. Free-form AI output must not drive import behavior.

Deterministic code remains responsible for validation and DB writes. It will apply confirmed or proposed mappings, verify every row, and classify rows as:

- `imported`: persisted as a valid position or enriched holding.
- `recoverable`: meaningful financial data requiring PB review before persistence.
- `quarantined`: unsafe to import because required values are invalid, contradictory, or unsupported.
- `garbage`: blank rows, subtotal rows, repeated headers, notes, disclosures, or non-portfolio rows.

Partial import becomes the target behavior for AI-assisted intake. Valid rows are persisted while recoverable, quarantined, and garbage rows are reported separately with source-row evidence. A new `partial_imported` status distinguishes partial success from a fully clean `imported` result.

The existing `holdings` table will be extended rather than replaced by a separate physical `positions` table. Domain language distinguishes:

- Position: symbol, market, and quantity.
- Cost basis: average cost, purchase amount, or book cost evidence, which may be missing.
- Enriched holding: a position combined with market price, optional cost basis, and deterministic metrics.

`holdings.avg_cost` will become nullable, with a cost-basis status such as `provided`, `missing`, `derived`, or `needs_review`. Missing cost basis must never be represented as zero. Cost-basis-dependent metrics such as PnL, return, contribution, and rebalance evidence must degrade when cost basis is missing.

We will add durable row-level audit storage for partial import. `portfolio_import_batches` remains the batch-level audit record, and a new import row ledger records each source row's status, raw row evidence, normalized payload, reason codes, and any linked imported holding or position.

PB-confirmed mappings will be reusable through schema profiles. A schema profile is based on source structure and verification metadata, not exact file content hash. When a later CSV matches a confirmed schema profile, deterministic verification is still rerun on all rows before persistence.

AI failure must not break the import flow. If the AI mapper is unavailable or returns invalid structured output, the system falls back to deterministic mapping and PB confirmation.

## Consequences

- The product can import the useful parts of messy real-world portfolio CSV files instead of failing the whole file.
- PBs can review unresolved rows after a browser refresh because row-level review state is durable, not only cached in the upload session.
- Same-format broker files can become mostly automatic after one confirmed mapping.
- Dashboard and analysis services must handle positions with missing cost basis and degrade cost-basis-dependent metrics instead of fabricating values.
- OpenAPI, backend schemas, database migrations, upload import services, frontend review UI, and browser smoke tests must be updated together.
- This increases implementation scope, so delivery will be split into milestones: durable partial import core, AI semantic mapper, then schema profile memory and UX.
