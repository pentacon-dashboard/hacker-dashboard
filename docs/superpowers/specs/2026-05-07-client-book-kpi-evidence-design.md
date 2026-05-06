# Customer Book KPI Evidence Panel Design

Date: 2026-05-07

## Purpose

Add click interactions to the customer-book selected-client dashboard KPI cards so a PB can immediately understand why each KPI number is shown. The primary goal is evidence clarity for demo and review: deterministic portfolio data explains the metric, and the UI does not imply unsupported investment advice.

## Scope

In scope:

- The selected customer dashboard panel on the customer-book home route.
- Only `SelectedClientDashboard` when `variant="clientBook"`.
- The five customer-book KPI cards: total assets, daily change, 30-day change, holdings count, and concentration risk.
- One inline evidence panel rendered below the KPI grid.

Out of scope:

- Applying the behavior to the general dashboard.
- Applying the behavior to `/clients/<client_id>` workspace KPI cards.
- Changing backend API contracts in the first implementation.
- LLM-generated explanations, personalized investment advice, or guaranteed-return language.

## Current Code Facts

- The customer-book dashboard already uses `SelectedClientDashboard` with `variant="clientBook"`.
- The current KPI cards are rendered with `KpiCard`.
- `PortfolioSummary` already exposes `total_value_krw`, `daily_change_*`, `period_change_pct`, `asset_class_breakdown`, `sector_breakdown`, `holdings`, `holdings_count`, `risk_score_pct`, and `dimension_breakdown`.
- Snapshots are available through `getSnapshots` and include date-level `total_value_krw`, `total_pnl_krw`, `asset_class_breakdown`, and `holdings_detail`.
- Current `risk_score_pct` is asset-class HHI based. The evidence panel must not describe it as a pure single-symbol concentration score.

## Interaction Model

- On initial load, the total-assets evidence panel is open by default.
- KPI cards behave like buttons.
- Only one KPI is selected at a time.
- Clicking another KPI replaces the inline evidence panel content.
- The evidence panel appears directly below the KPI card grid and above the existing chart/allocation/top-holdings sections.
- Each panel has one small secondary action, never an action cluster.

## KPI Card Visual Rules

- Keep the cards visually close to the existing dashboard cards.
- Use `ring` and subtle selected background for the active card. Do not change border width on selection, because that would shift card dimensions.
- Keep metric values in `text-foreground`; do not recolor an entire selected card with `text-primary`.
- Preserve separate color semantics for labels, values, deltas, and selected state.
- Cards must have equal minimum height across all five KPI cards.
- Use `min-w-0`, safe wrapping, and truncation where needed so long Korean labels, compact KRW values, and risk labels do not overlap.
- Hover, focus-visible, selected, and disabled/loading states need separate visual treatment.
- In light and dark mode, selected-card text, delta colors, and degraded-state text must maintain readable contrast.

## Evidence Panel Structure

Each evidence panel uses the same outer structure:

- Header: KPI label, current value, one-sentence deterministic summary.
- Main evidence block: the strongest explanation for the KPI.
- Supporting evidence block: one secondary explanation or short list.
- Calculation and source disclosure: collapsible details for metric formula and source fields.
- Secondary action: one KPI-specific navigation/action button.
- Degraded blocks: shown only where data is unavailable or not safe to compute.

The panel should use a full-width layout under the KPI grid. Tables and dense rows must support horizontal overflow instead of overflowing into neighboring content.

## Secondary Action Targets

Each evidence panel has exactly one secondary action:

- Total assets: `고객 상세 보기` links to `/clients/<client_id>`.
- Daily change: `관련 뉴스 보기` links to `/news?client_id=<client_id>`.
- 30-day change: `추이 자세히 보기` scrolls to the customer-book asset trend section. Add a stable `id="client-book-asset-trend"` to that section during implementation.
- Holdings count: `보유 테이블 보기` links to `/clients/<client_id>#holdings`. Add or preserve a stable `id="holdings"` target in the workspace holdings section.
- Concentration risk: `리밸런싱 검토` links to `/clients/<client_id>#rebalance`. Add or preserve a stable `id="rebalance"` target in the workspace rebalance section.

## KPI Evidence Content

### Total Assets

Main evidence:

- Asset-class value and weight breakdown using `summary.asset_class_breakdown` and `summary.total_value_krw`.

Supporting evidence:

- Top holdings by `value_krw`.

Disclosure:

- Total value is the sum of current holding values in KRW.
- Source fields: `summary.total_value_krw`, `summary.asset_class_breakdown`, `summary.holdings`.

Secondary action:

- `고객 상세 보기`.

### Daily Change

Main evidence:

- Today contribution leaders and laggards when reliable per-holding daily data is available.

Supporting evidence:

- Asset-class daily movement summary when reliable source data exists.

Degraded behavior:

- If current summary and snapshots cannot safely identify per-holding daily contribution, show `현재 데이터로 종목별 일간 기여를 산출할 수 없습니다` for that block.
- Do not infer contribution from total PnL or current allocation.

Disclosure:

- Source fields: `summary.daily_change_krw`, `summary.daily_change_pct`, previous snapshot, and any available snapshot `holdings_detail`.

Secondary action:

- `관련 뉴스 보기`.

### 30-Day Change

Main evidence:

- Period trend using snapshots, including start value, end value, high, low, and period return.

Supporting evidence:

- 7-day, 30-day, and 90-day comparison only when enough snapshot data exists.

Degraded behavior:

- Show symbol-level 30-day contribution only when the data supports it directly.
- Otherwise show a local degraded block instead of a contribution table.

Disclosure:

- Source fields: `summary.period_change_pct`, `summary.period_days`, and `snapshots`.

Secondary action:

- `추이 자세히 보기`.

### Holdings Count

Main evidence:

- Holdings count split by market or asset class.

Supporting evidence:

- Short top-holdings list by value.

Degraded behavior:

- If holdings are hidden by display-safety rules, show the hidden count and why those rows are excluded from display.

Disclosure:

- Source fields: `summary.holdings_count`, `summary.holdings`, and display-safety filtering.

Secondary action:

- `보유 테이블 보기`.

### Concentration Risk

Main evidence:

- Asset-class HHI-style concentration explanation based on current backend `risk_score_pct`.

Supporting evidence:

- Top holding weights as context, clearly separate from the displayed risk score formula.

Degraded behavior:

- If total value is zero or asset-class data is unavailable, show insufficient-data messaging for the score explanation.

Disclosure:

- Source fields: `summary.risk_score_pct`, `summary.asset_class_breakdown`, `summary.total_value_krw`, and `summary.holdings`.
- The risk score is asset-class concentration, not guaranteed loss probability and not a direct recommendation.

Secondary action:

- `리밸런싱 검토`.

## Data And Compliance Rules

- Deterministic code calculates all metrics shown in the panel.
- The panel may explain values but must not invent missing inputs.
- Numeric statements must cite a source field or computed deterministic derivative.
- Blocks with insufficient evidence must degrade locally instead of being hidden.
- Do not present guaranteed returns, certain price direction, or unsupported personalized investment advice.
- Concentration-risk copy must explain the score basis without telling the PB to buy or sell.

## Accessibility

- KPI cards should be implemented as buttons or equivalent controls.
- The selected card should expose `aria-expanded` and `aria-controls` for the panel.
- Keyboard focus must remain visible.
- The active panel heading should be programmatically associated with the panel region.
- Color must not be the only indication of positive/negative movement or degraded state.
- Use visible signs such as `+`, `-`, `기여`, `차감`, `데이터 부족`, and clear labels.

## Responsive Behavior

- KPI grid remains two columns on small widths, three columns on medium widths, and five columns at the customer-book wide breakpoint.
- The evidence panel spans the full grid width at every breakpoint.
- Panel internals may switch from multi-column to single-column layouts on narrow widths.
- Long symbols, market names, and KRW values must not overlap or escape the panel.
- The panel should avoid large height swings between KPI selections.

## Testing Plan

Frontend unit tests:

- Total-assets evidence panel renders by default in customer-book variant.
- Clicking each KPI changes the panel heading and main content.
- Customer-book-only behavior: general dashboard variant does not render the evidence panel.
- Daily-change unsupported per-holding contribution renders a degraded block.
- Hidden holdings count is surfaced in holdings evidence when applicable.
- Concentration-risk copy reflects asset-class HHI semantics.

Manual/browser verification:

- Open the customer-book home route and select a customer.
- Verify total-assets evidence is visible on first load.
- Click all five KPI cards.
- Check light and dark mode contrast.
- Check narrow mobile, tablet, and desktop widths for text overlap.
- Confirm secondary actions navigate or target the intended section without mock-only data.

## Implementation Notes

- Keep the first implementation frontend-only if existing `summary` and `snapshots` are enough.
- If a future version needs new backend evidence fields, add API contract changes intentionally and regenerate shared OpenAPI/types.
- Prefer a small KPI evidence component with deterministic helper functions over embedding all logic directly in `dashboard-home.tsx`.
- Keep the existing dashboard sections intact below the new panel.

## Deferred Decisions

- Per-holding daily contribution stays degraded in the first implementation if snapshot `holdings_detail` cannot be compared holding-by-holding with clear symbol identity and date alignment.
- Backend fields for per-holding period contribution are intentionally deferred until a separate API contract change is approved.
