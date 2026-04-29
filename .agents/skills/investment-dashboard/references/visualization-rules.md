# Visualization Rules

## Layout

Dashboard order:

1. KPI strip: value, PnL/return, risk, Router result, gate status.
2. Primary visualization.
3. Insight card.
4. Holdings/action/data table.
5. Evidence and Router/Gate detail.
6. Report preview or export action when all report gates pass.

## Chart Choice

- Close/time series: line chart.
- OHLC: candlestick.
- Allocation: donut or bar.
- Target drift: zero-centered diverging bar.
- Holdings/actions: sortable table.
- Risk: badge, gauge, alert.
- Evidence: compact panel with row/metric/source reference.
- Client briefing report: sectioned preview with evidence chips and gate status.

## UI Quality

- Use existing shadcn/ui and Tailwind patterns.
- Keep loading, empty, error, and degraded states.
- Avoid nested cards.
- Mobile order: KPI, insight, chart, table, evidence.
- Text must not overflow cards, buttons, badges, or table cells.
- Report actions should be disabled or clearly degraded when evidence or gate checks fail.
