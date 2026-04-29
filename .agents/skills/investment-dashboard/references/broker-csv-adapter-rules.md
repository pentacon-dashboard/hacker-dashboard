# Broker CSV Adapter Rules

## Purpose

Normalize broker, exchange, or customer-provided CSV files into the project portfolio schema while preserving source evidence and mapping confidence.

## Intake

- Inspect column names, the first 5 rows, symbol patterns, market names, currency values, numeric formats, and account fields.
- Preserve original column names and source row indexes.
- Do not infer customer identity, risk profile, or investment objective from filenames or missing data.

## Standard Fields

- `symbol`: ticker, code, pair, issue code, 종목코드, 티커
- `name`: asset name, 종목명, 상품명
- `quantity`: qty, quantity, shares, units, 보유수량, 수량
- `avg_price`: avg_price, avg_cost, average_price, 매입가, 평균단가
- `price`: price, close, trade_price, current_price, 현재가, 평가가격
- `currency`: currency, ccy, 통화
- `market`: market, exchange, broker, 거래소, 시장
- `account`: account, account_no, 계좌, 계좌번호
- `client_id`: client_id, customer_id, 고객ID

## Confidence Rules

- Auto-map only when confidence is at least 0.95.
- Return `needs_review` for ambiguous, duplicate, or low-confidence mappings.
- Include `mapping_reason` for every mapped field.
- Include `unmapped_columns` so PB users can review ignored fields.

## Fail-Safe

- Never coerce missing numeric values to zero unless zero is explicitly present in the source.
- Reject or flag negative prices, invalid quantities, invalid dates, or unsupported encodings.
- If required fields cannot be mapped, return `insufficient_data` instead of fabricating holdings.
