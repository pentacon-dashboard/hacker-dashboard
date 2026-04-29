# Quant Metric Rules

## Purpose

Ensure all financial metrics are calculated by deterministic backend code before LLM narrative or report generation.

## Required Metrics

- Total value: sum of validated position values and cash.
- Total cost: sum of validated quantity times average cost.
- PnL: `total_value - total_cost`.
- PnL%: `pnl / total_cost * 100` when total cost is positive.
- Period return: `(last - first) / first * 100` for valid time series.
- Volatility: standard deviation of observed log returns.
- MDD: minimum drawdown from running peak.
- Allocation: position value divided by total portfolio value.
- HHI: sum of squared allocation weights.
- Drift: `current_allocation - target_allocation`.
- Rebalance quantity: target value delta divided by validated reference price.

## Rules

- LLMs never create numeric metrics.
- Metrics with insufficient observations return `insufficient_data`.
- Division by zero returns a validation issue, not zero.
- Currency-converted metrics must cite FX rate, date, and source.
- Rebalance actions must remain available when LLM explanation fails.

## Report Use

Report sections may cite only metrics returned by deterministic services.

Professional terms are allowed only when their backing metric exists:

- Alpha requires benchmark return.
- Beta requires benchmark covariance/variance.
- Correlation requires paired return observations.
- Sharpe ratio requires return series and risk-free assumption.
