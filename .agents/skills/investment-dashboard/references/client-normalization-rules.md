# Client Normalization Rules

## Purpose

Merge multiple accounts, brokers, markets, and currencies into a client-level portfolio view without losing source traceability.

## Required Context

- `client_id` or explicitly selected client context is required for client-level reporting.
- `account`, `broker`, `market`, and `currency` should be preserved when present.
- Missing client context must produce portfolio-level analysis only, not client-specific claims.

## Normalization

- Group holdings by client, account, broker, market, currency, asset class, and symbol.
- Preserve source rows for each consolidated holding.
- Separate realized PnL, unrealized PnL, cash, deposits, and holdings when source data supports it.
- Keep currency conversion assumptions explicit with rate, date, and source evidence.

## Client Report Safety

- Do not infer risk profile, investment objective, suitability, age, income, or financial condition.
- If `risk_profile` exists, quote it as provided and attach source evidence.
- If multiple accounts conflict, show warnings instead of silently overwriting values.

## Output

Use a normalized client portfolio object with:

- `client_context`
- `accounts`
- `holdings`
- `cash`
- `currency_exposure`
- `source_rows`
- `normalization_warnings`
