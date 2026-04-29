# Report Rules

## Purpose

Generate PB-facing and client-facing investment briefing reports from validated dashboard data.

## Required Section Order

1. Summary
2. Performance Contribution
3. Risk Analysis
4. Rebalance Proposal
5. PB Opinion

## Section Rules

- Summary: cite total value, PnL, allocation, or risk metrics.
- Performance Contribution: cite position-level or asset-class contribution metrics.
- Risk Analysis: cite concentration, volatility, MDD, currency exposure, or validation warnings.
- Rebalance Proposal: cite deterministic drift and rebalance quantity outputs.
- PB Opinion: explain the tradeoff in professional language without guarantees or pressure.

## Tone

- Korean by default for user-facing report text.
- Use concise PB/WM language.
- Use terms such as alpha, beta, correlation, duration, and Sharpe only when calculated metrics exist.
- Explain uncertainty and missing data clearly.

## Output Protocol

Report generation returns:

- `status`: `success`, `warning`, `degraded`, or `insufficient_data`
- `client_context`
- `metrics`
- `sections`
- `evidence`
- `gate_results`
- `export_ready`

## Fail-Safe

- Do not fabricate missing client context.
- Do not create customer-facing report text when evidence or critique gates fail.
- Do not turn rebalance proposals into direct investment orders.
- If an LLM fails, keep deterministic metrics and return a degraded report draft state.
