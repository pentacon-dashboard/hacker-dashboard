# Client Normalization Rules

## Purpose

Merge multiple accounts, brokers, markets, and currencies into a client-level portfolio view without losing source traceability.

## Required Context

- `client_id` or explicitly selected client context is required for client-level reporting.
- `account`, `broker`, `market`, and `currency` should be preserved when present.
- Missing client context must produce portfolio-level analysis only, not client-specific claims.
- Demo client links must be backed by actual ledger rows unless the test explicitly covers an empty state.

## Normalization

- Group holdings by client, account, broker, market, currency, asset class, and symbol.
- Preserve source rows for each consolidated holding.
- Separate realized PnL, unrealized PnL, cash, deposits, and holdings when source data supports it.
- Keep currency conversion assumptions explicit with rate, date, and source evidence.

## Client Report Safety

- Do not infer risk profile, investment objective, suitability, age, income, or financial condition.
- If `risk_profile` exists, quote it as provided and attach source evidence.
- If multiple accounts conflict, show warnings instead of silently overwriting values.

## Demo Ledger Contract

- A route such as `/clients/client-003` is demo-ready only when `/portfolio/summary?client_id=client-003` returns `holdings_count > 0` and `total_value_krw > 0`.
- The customer list and client workspace must agree on client ID, display name, holdings count, and AUM source.
- If a client is created by upload/import, the post-import route must be validated against persisted holdings, not only a client ID returned by the UI flow.
- Treat a populated root customer list plus an empty client detail route as a blocking data-integrity issue.
- Treat a client detail page stuck in skeleton/loading state as a frontend runtime issue, not a successful smoke.

## Output

Use a normalized client portfolio object with:

- `client_context`
- `accounts`
- `holdings`
- `cash`
- `currency_exposure`
- `source_rows`
- `normalization_warnings`
