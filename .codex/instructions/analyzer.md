# Analyzer Instructions

## Router

Use deterministic classification before LLM routing:

- `portfolio`: `market/code/quantity/avg_cost` or equivalent holdings columns.
- `crypto`: `KRW-BTC`, `BTC-USD`, `BTC/USDT`, `upbit`, `binance`.
- `stock`: `005930.KS`, `000660.KS`, `AAPL`, `TSLA`, `NVDA`.
- `fx`: `USDKRW=X`, `USD/KRW`, `EURUSD`, `rate`, `exchange_rate`.
- `macro`: `cpi`, `gdp`, `unemployment`, `yield_10y`, `fed_rate`, `inflation`.
- `mixed`: two or more credible asset classes.

## Metrics

- Return: `(last - first) / first * 100`.
- Volatility: standard deviation of observed log returns.
- MDD: minimum drawdown from running peak.
- HHI: sum of squared weights.
- Drift: `current_allocation - target_allocation`.

## LLM Output

- LLMs may write narrative, not new facts.
- Every claim needs evidence.
- Confidence reflects data completeness and gate quality.
- Forbidden terms include guaranteed returns, certainty language, and direct personalized advice.
