# Evidence Compliance Rules

## Purpose

Make every investment insight, dashboard warning, and client report sentence traceable to source data or deterministic calculations.

## Evidence Types

- `row`: source CSV row index or normalized row id.
- `metric`: deterministic service output name.
- `api_data`: market, FX, news, or search service response id.
- `fixture`: demo or golden fixture id.

## Required Links

- Every numeric claim must cite a metric or source row.
- Every factual claim about a holding, account, market, or currency must cite source rows or API data.
- Every report section must include at least one evidence item.
- Every rebalance explanation must cite drift, target allocation, current allocation, and reference price.

## Blocked Claims

- Guaranteed returns.
- Certain future price direction.
- Unsupported causality.
- Personalized suitability claims without explicit input.
- Tickers, prices, weights, client profiles, or dates absent from source data.

## Gate Behavior

- Missing evidence returns degraded or `insufficient_data`.
- Evidence mismatch blocks normal rendering.
- LLM unavailability may keep deterministic metrics visible, but report narrative must be degraded.
- Customer-facing report export is allowed only after schema, domain, evidence, and critique gates pass.
