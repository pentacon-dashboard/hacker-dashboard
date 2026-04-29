# Analysis Rules

## Intake

- Preserve original columns for evidence.
- Normalize aliases for symbol, date, price, quantity, cost, market, currency, account, broker, and client when present.
- Preserve mapping confidence and `needs_review` fields from broker CSV adapters.
- Reject or flag impossible values such as negative prices, invalid dates, or unsupported allocation totals.
- Do not convert missing values to zero unless zero is meaningful in that domain.

## Router

Deterministic rules are preferred over LLM routing.

- `portfolio`: holdings columns such as `market`, `code`, `quantity`, `avg_cost`.
- `crypto`: `KRW-BTC`, `BTC-USD`, `BTC/USDT`, `upbit`, `binance`.
- `stock`: KRX codes with `.KS`/`.KQ` or US tickers such as `AAPL`, `TSLA`, `NVDA`.
- `fx`: `USDKRW=X`, `USD/KRW`, `EURUSD`, exchange-rate columns.
- `macro`: CPI, GDP, unemployment, yield, Fed rate, inflation.
- `mixed`: two or more credible classes.

Router output must include `asset_class`, `router_reason`, `confidence`, and symbols when available.

## Metrics

- Period return: `(last - first) / first * 100`.
- Volatility: standard deviation of observed log returns.
- MDD: minimum `(value - running_peak) / running_peak * 100`.
- SMA20/SMA60 only with enough observations.
- HHI: sum of squared weights.
- PnL: `total_value - total_cost`.
- Drift: `current_allocation - target_allocation`.
- Rebalance quantity: target value delta divided by validated execution or reference price.

## Rebalance

- Services generate actions deterministically.
- LLM only explains existing actions.
- Missing price data creates warnings and degraded confidence.
- Actions remain available when LLM analysis fails.

## PB/WM Reporting

- Client report sections consume deterministic metrics and validated evidence only.
- Section-level evidence is required for summary, performance contribution, risk analysis, rebalance proposal, and PB opinion.
- Report generation returns degraded or `insufficient_data` when mapping, metrics, or evidence are incomplete.
