# Client Book KPI Evidence Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a customer-book-only KPI click interaction that opens an inline deterministic evidence panel for total assets, daily change, 30-day change, holdings count, and concentration risk.

**Architecture:** Keep backend contracts unchanged. Add focused frontend helper functions for deterministic evidence derivation, an accessible KPI evidence panel component, small optional interactive props on the existing KPI card, and wire the behavior only into `SelectedClientDashboard` when `variant="clientBook"`.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind, TanStack Query, Vitest, React Testing Library.

---

## File Structure

- Create `frontend/components/dashboard/kpi-evidence-utils.ts`
  - Pure deterministic helpers for asset-class rows, top holdings, holdings distribution, snapshot stats, HHI explanation inputs, and degraded-state detection.
- Create `frontend/components/dashboard/kpi-evidence-utils.test.ts`
  - Unit tests for all helper behavior, especially degraded cases.
- Create `frontend/components/dashboard/kpi-evidence-panel.tsx`
  - Presentational evidence panel for the five KPI evidence types.
  - Owns layout, source disclosure, degraded blocks, and one secondary action per KPI.
- Create `frontend/components/dashboard/kpi-evidence-panel.test.tsx`
  - Component tests for default total-assets view, degraded daily-change view, concentration-risk semantics, and secondary action targets.
- Modify `frontend/components/dashboard/kpi-card.tsx`
  - Add optional button behavior without changing current non-interactive usage.
- Modify `frontend/components/dashboard/dashboard-home.tsx`
  - Track selected KPI state in `SelectedClientDashboard`.
  - Render interactive KPI cards and evidence panel only for `variant="clientBook"`.
  - Add `id="client-book-asset-trend"` to the customer-book trend section.
- Modify `frontend/components/dashboard/dashboard-home.test.tsx`
  - Extend existing customer-book tests for default panel, KPI click switching, customer-book-only behavior, and links.
- Modify `frontend/components/clients/client-workspace.tsx`
  - Add `id="holdings"` and `id="rebalance"` anchors to existing holdings and rebalance sections.

---

### Task 1: Deterministic Evidence Helpers

**Files:**
- Create: `frontend/components/dashboard/kpi-evidence-utils.ts`
- Create: `frontend/components/dashboard/kpi-evidence-utils.test.ts`

- [ ] **Step 1: Write failing tests for helper outputs**

Create `frontend/components/dashboard/kpi-evidence-utils.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { HoldingDetail, PortfolioSummary, SnapshotResponse } from "@/lib/api/portfolio";
import {
  buildAssetClassEvidenceRows,
  buildHoldingDistributionRows,
  buildPeriodSnapshotStats,
  buildTopHoldingWeightRows,
  classifyMarketAssetClass,
  hasComparableHoldingSnapshots,
  hhiFormulaLabel,
} from "./kpi-evidence-utils";

function holding(overrides: Partial<HoldingDetail>): HoldingDetail {
  return {
    id: 1,
    market: "naver_kr",
    code: "005930",
    quantity: "10",
    avg_cost: "70000",
    currency: "KRW",
    current_price: "80000",
    current_price_krw: "80000",
    value_krw: "800000",
    cost_krw: "700000",
    pnl_krw: "100000",
    pnl_pct: "14.29",
    ...overrides,
  };
}

const summary = {
  user_id: "pb-demo",
  client_id: "client-001",
  client_name: "고객 A",
  total_value_krw: "100000000",
  total_cost_krw: "90000000",
  total_pnl_krw: "10000000",
  total_pnl_pct: "11.11",
  daily_change_krw: "120000",
  daily_change_pct: "0.12",
  asset_class_breakdown: { stock_kr: "0.70", stock_us: "0.30" },
  sector_breakdown: {},
  holdings: [
    holding({ id: 1, market: "naver_kr", code: "005930", value_krw: "70000000" }),
    holding({ id: 2, market: "nasdaq", code: "AAPL", currency: "USD", value_krw: "30000000" }),
  ],
  holdings_count: 2,
  worst_asset_pct: "-2.50",
  risk_score_pct: "58.00",
  period_change_pct: "2.40",
  period_days: 30,
  dimension_breakdown: [],
  win_rate_pct: "50.00",
  market_leaders: [],
} satisfies PortfolioSummary;

function snapshot(id: number, date: string, value: string): SnapshotResponse {
  return {
    id,
    user_id: "pb-demo",
    client_id: "client-001",
    client_name: "고객 A",
    snapshot_date: date,
    total_value_krw: value,
    total_pnl_krw: "0",
    asset_class_breakdown: {},
    holdings_detail: [],
    created_at: `${date}T00:00:00Z`,
  };
}

describe("kpi evidence utils", () => {
  it("builds asset-class evidence rows with deterministic KRW values", () => {
    expect(buildAssetClassEvidenceRows(summary)).toEqual([
      { key: "stock_kr", label: "국내주식", ratio: 0.7, valueKrw: 70000000 },
      { key: "stock_us", label: "미국주식", ratio: 0.3, valueKrw: 30000000 },
    ]);
  });

  it("sorts top holdings by portfolio weight", () => {
    expect(buildTopHoldingWeightRows(summary.holdings, 100000000, 2)).toMatchObject([
      { code: "005930", market: "naver_kr", weightPct: 70 },
      { code: "AAPL", market: "nasdaq", weightPct: 30 },
    ]);
  });

  it("classifies markets using backend-compatible asset classes", () => {
    expect(classifyMarketAssetClass("upbit")).toBe("crypto");
    expect(classifyMarketAssetClass("nasdaq")).toBe("stock_us");
    expect(classifyMarketAssetClass("naver_kr")).toBe("stock_kr");
    expect(classifyMarketAssetClass("unknown")).toBe("other");
  });

  it("builds holding distribution rows by asset class", () => {
    expect(buildHoldingDistributionRows(summary.holdings)).toEqual([
      { key: "stock_kr", label: "국내주식", count: 1 },
      { key: "stock_us", label: "미국주식", count: 1 },
    ]);
  });

  it("builds snapshot period stats from ordered values", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "90000000"),
        snapshot(2, "2026-04-20", "110000000"),
        snapshot(3, "2026-05-07", "100000000"),
      ]),
    ).toEqual({
      startDate: "2026-04-07",
      endDate: "2026-05-07",
      startValueKrw: 90000000,
      endValueKrw: 100000000,
      highValueKrw: 110000000,
      lowValueKrw: 90000000,
      returnPct: 11.11111111111111,
    });
  });

  it("returns null snapshot stats when there are fewer than two snapshots", () => {
    expect(buildPeriodSnapshotStats([snapshot(1, "2026-05-07", "100000000")])).toBeNull();
  });

  it("requires aligned holdings_detail for comparable holding snapshots", () => {
    const comparable = [
      { ...snapshot(1, "2026-05-06", "90000000"), holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "10" }] },
      { ...snapshot(2, "2026-05-07", "100000000"), holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "12" }] },
    ];
    const notComparable = [
      { ...snapshot(1, "2026-05-06", "90000000"), holdings_detail: [] },
      { ...snapshot(2, "2026-05-07", "100000000"), holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "12" }] },
    ];
    expect(hasComparableHoldingSnapshots(comparable)).toBe(true);
    expect(hasComparableHoldingSnapshots(notComparable)).toBe(false);
  });

  it("uses asset-class HHI language for concentration score", () => {
    expect(hhiFormulaLabel).toContain("자산군");
    expect(hhiFormulaLabel).toContain("HHI");
  });
});
```

- [ ] **Step 2: Run helper tests to verify they fail**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-evidence-utils.test.ts
```

Expected: FAIL because `./kpi-evidence-utils` does not exist.

- [ ] **Step 3: Implement the helper module**

Create `frontend/components/dashboard/kpi-evidence-utils.ts`:

```ts
import type {
  HoldingDetail,
  PortfolioSummary,
  SnapshotResponse,
} from "@/lib/api/portfolio";

const MARKET_TO_ASSET_CLASS: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock_us",
  naver_kr: "stock_kr",
  krx: "stock_kr",
  nasdaq: "stock_us",
  nyse: "stock_us",
};

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "국내주식",
  stock_us: "미국주식",
  crypto: "가상자산",
  cash: "현금",
  fx: "외화",
  other: "기타",
};

export const hhiFormulaLabel =
  "자산군별 비중 제곱의 합(HHI)을 0~100 점수로 환산한 집중도 지표";

export interface AssetClassEvidenceRow {
  key: string;
  label: string;
  ratio: number;
  valueKrw: number;
}

export interface HoldingWeightRow {
  id: number;
  market: string;
  code: string;
  valueKrw: number;
  pnlPct: number;
  weightPct: number;
}

export interface HoldingDistributionRow {
  key: string;
  label: string;
  count: number;
}

export interface SnapshotPeriodStats {
  startDate: string;
  endDate: string;
  startValueKrw: number;
  endValueKrw: number;
  highValueKrw: number;
  lowValueKrw: number;
  returnPct: number;
}

function toNumber(value: number | string | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function labelAssetClass(key: string): string {
  return ASSET_CLASS_LABELS[key] ?? key;
}

function holdingIdentity(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const market = String(record.market ?? "").trim().toLowerCase();
  const code = String(record.code ?? "").trim().toUpperCase();
  const valueKrw = record.value_krw;
  if (!market || !code || valueKrw == null || !Number.isFinite(Number(valueKrw))) {
    return null;
  }
  return `${market}:${code}`;
}

export function classifyMarketAssetClass(market: string): string {
  return MARKET_TO_ASSET_CLASS[market.toLowerCase()] ?? "other";
}

export function buildAssetClassEvidenceRows(
  summary: PortfolioSummary,
): AssetClassEvidenceRow[] {
  const total = toNumber(summary.total_value_krw);
  return Object.entries(summary.asset_class_breakdown)
    .map(([key, ratio]) => {
      const numericRatio = toNumber(ratio);
      return {
        key,
        label: labelAssetClass(key),
        ratio: numericRatio,
        valueKrw: total * numericRatio,
      };
    })
    .sort((a, b) => b.ratio - a.ratio);
}

export function buildTopHoldingWeightRows(
  holdings: HoldingDetail[],
  totalValueKrw: number,
  limit = 5,
): HoldingWeightRow[] {
  return [...holdings]
    .sort((a, b) => toNumber(b.value_krw) - toNumber(a.value_krw))
    .slice(0, limit)
    .map((holding) => {
      const valueKrw = toNumber(holding.value_krw);
      return {
        id: holding.id,
        market: holding.market,
        code: holding.code,
        valueKrw,
        pnlPct: toNumber(holding.pnl_pct),
        weightPct: totalValueKrw > 0 ? (valueKrw / totalValueKrw) * 100 : 0,
      };
    });
}

export function buildHoldingDistributionRows(
  holdings: HoldingDetail[],
): HoldingDistributionRow[] {
  const counts = new Map<string, number>();
  holdings.forEach((holding) => {
    const key = classifyMarketAssetClass(holding.market);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return Array.from(counts.entries())
    .map(([key, count]) => ({ key, label: labelAssetClass(key), count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function buildPeriodSnapshotStats(
  snapshots: SnapshotResponse[],
): SnapshotPeriodStats | null {
  const ordered = [...snapshots].sort((a, b) =>
    a.snapshot_date.localeCompare(b.snapshot_date),
  );
  if (ordered.length < 2) return null;

  const start = ordered[0]!;
  const end = ordered[ordered.length - 1]!;
  const values = ordered.map((snapshot) => toNumber(snapshot.total_value_krw));
  const startValueKrw = toNumber(start.total_value_krw);
  const endValueKrw = toNumber(end.total_value_krw);

  return {
    startDate: start.snapshot_date,
    endDate: end.snapshot_date,
    startValueKrw,
    endValueKrw,
    highValueKrw: Math.max(...values),
    lowValueKrw: Math.min(...values),
    returnPct:
      startValueKrw > 0 ? ((endValueKrw - startValueKrw) / startValueKrw) * 100 : 0,
  };
}

export function hasComparableHoldingSnapshots(snapshots: SnapshotResponse[]): boolean {
  const ordered = [...snapshots].sort((a, b) =>
    a.snapshot_date.localeCompare(b.snapshot_date),
  );
  if (ordered.length < 2) return false;
  const first = ordered[0]!;
  const last = ordered[ordered.length - 1]!;
  if (first.holdings_detail.length === 0 || last.holdings_detail.length === 0) {
    return false;
  }

  const firstIds = new Set(first.holdings_detail.map(holdingIdentity).filter(Boolean));
  const lastIds = new Set(last.holdings_detail.map(holdingIdentity).filter(Boolean));
  if (firstIds.size === 0 || lastIds.size === 0) return false;
  return Array.from(lastIds).some((id) => firstIds.has(id));
}
```

- [ ] **Step 4: Run helper tests and typecheck the helper**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-evidence-utils.test.ts
cd frontend && npm run typecheck
```

Expected: helper test PASS; typecheck PASS.

- [ ] **Step 5: Commit helper work**

```bash
git add frontend/components/dashboard/kpi-evidence-utils.ts frontend/components/dashboard/kpi-evidence-utils.test.ts
git commit -m "구현: KPI 근거 계산 헬퍼 추가"
```

---

### Task 2: Accessible Interactive KPI Card

**Files:**
- Modify: `frontend/components/dashboard/kpi-card.tsx`
- Create: `frontend/components/dashboard/kpi-card.test.tsx`

- [ ] **Step 1: Write failing tests for existing and interactive card modes**

Create `frontend/components/dashboard/kpi-card.test.tsx`:

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { KpiCard } from "./kpi-card";

describe("KpiCard", () => {
  it("renders as a non-interactive card by default", () => {
    renderWithProviders(<KpiCard label="총자산" value="₩1.00B" testId="plain-kpi" />);
    expect(screen.getByTestId("plain-kpi").tagName).toBe("DIV");
    expect(screen.queryByRole("button", { name: /총자산/ })).not.toBeInTheDocument();
  });

  it("renders as an accessible selected button when onClick is provided", () => {
    const onClick = vi.fn();
    renderWithProviders(
      <KpiCard
        label="총자산"
        value="₩1.00B"
        delta="+1.00%"
        onClick={onClick}
        selected
        controlsId="kpi-evidence-panel"
        testId="button-kpi"
      />,
    );

    const button = screen.getByRole("button", { name: /총자산/ });
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("aria-controls", "kpi-evidence-panel");
    expect(button.className).toContain("ring-2");
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run card tests to verify they fail**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-card.test.tsx
```

Expected: FAIL because `KpiCardProps` does not accept `onClick`, `selected`, or `controlsId`.

- [ ] **Step 3: Add optional interactive props to KpiCard**

Modify `frontend/components/dashboard/kpi-card.tsx` so the props and return logic match this structure:

```tsx
interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaValue?: number;
  icon?: React.ReactNode;
  accent?: KpiAccent;
  tone?: "neutral" | "positive" | "negative";
  testId?: string;
  onClick?: () => void;
  selected?: boolean;
  controlsId?: string;
}
```

Use this class composition for both `div` and `button` modes:

```tsx
const cardClassName = cn(
  "rounded-xl border bg-card p-4 shadow-sm transition-colors",
  "flex min-h-[118px] min-w-0 flex-col gap-2 text-left",
  onClick &&
    "w-full cursor-pointer hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
  selected && "bg-primary/5 ring-2 ring-primary/35",
);

const content = (
  <>
    <div className="flex min-w-0 items-start justify-between gap-2">
      <span className="min-w-0 overflow-hidden text-ellipsis break-keep text-xs font-medium leading-tight text-muted-foreground">
        {label}
      </span>
      {icon && (
        <span
          aria-hidden="true"
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
            accentBg[accent],
          )}
        >
          {icon}
        </span>
      )}
    </div>
    <div className="flex min-w-0 flex-col items-start gap-1">
      <span
        className="min-w-0 max-w-full overflow-hidden text-ellipsis break-keep text-base font-semibold leading-tight text-foreground sm:text-lg md:text-xl"
        title={value}
      >
        {value}
      </span>
      {delta && (
        <span className={cn("max-w-full shrink-0 overflow-hidden text-ellipsis break-keep text-xs font-semibold leading-tight", deltaColor)}>
          {delta}
        </span>
      )}
    </div>
  </>
);

if (onClick) {
  return (
    <button
      type="button"
      data-testid={testId}
      className={cardClassName}
      onClick={onClick}
      aria-expanded={selected}
      aria-controls={controlsId}
    >
      {content}
    </button>
  );
}

return (
  <div data-testid={testId} className={cardClassName}>
    {content}
  </div>
);
```

Keep the existing `deltaColor` and `accentBg` logic.

- [ ] **Step 4: Run card tests and existing dashboard tests**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-card.test.tsx components/dashboard/dashboard-home.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit interactive card work**

```bash
git add frontend/components/dashboard/kpi-card.tsx frontend/components/dashboard/kpi-card.test.tsx
git commit -m "구현: KPI 카드 선택 상태 지원"
```

---

### Task 3: KPI Evidence Panel Component

**Files:**
- Create: `frontend/components/dashboard/kpi-evidence-panel.tsx`
- Create: `frontend/components/dashboard/kpi-evidence-panel.test.tsx`

- [ ] **Step 1: Write failing panel tests**

Create `frontend/components/dashboard/kpi-evidence-panel.test.tsx`:

```tsx
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import type { PortfolioSummary, SnapshotResponse } from "@/lib/api/portfolio";
import { KpiEvidencePanel, type KpiEvidenceKey } from "./kpi-evidence-panel";

const summary = {
  user_id: "pb-demo",
  client_id: "client-001",
  client_name: "고객 A",
  total_value_krw: "100000000",
  total_cost_krw: "90000000",
  total_pnl_krw: "10000000",
  total_pnl_pct: "11.11",
  daily_change_krw: "120000",
  daily_change_pct: "0.12",
  asset_class_breakdown: { stock_kr: "0.70", stock_us: "0.30" },
  sector_breakdown: {},
  holdings: [
    {
      id: 1,
      market: "naver_kr",
      code: "005930",
      quantity: "10",
      avg_cost: "70000",
      currency: "KRW",
      current_price: "80000",
      current_price_krw: "80000",
      value_krw: "70000000",
      cost_krw: "60000000",
      pnl_krw: "10000000",
      pnl_pct: "16.67",
    },
    {
      id: 2,
      market: "nasdaq",
      code: "AAPL",
      quantity: "5",
      avg_cost: "150",
      currency: "USD",
      current_price: "170",
      current_price_krw: "230000",
      value_krw: "30000000",
      cost_krw: "27000000",
      pnl_krw: "3000000",
      pnl_pct: "11.11",
    },
  ],
  holdings_count: 2,
  worst_asset_pct: "11.11",
  risk_score_pct: "58.00",
  period_change_pct: "2.40",
  period_days: 30,
  dimension_breakdown: [],
  win_rate_pct: "100.00",
  market_leaders: [],
} satisfies PortfolioSummary;

const snapshots: SnapshotResponse[] = [
  {
    id: 1,
    user_id: "pb-demo",
    client_id: "client-001",
    client_name: "고객 A",
    snapshot_date: "2026-04-07",
    total_value_krw: "90000000",
    total_pnl_krw: "0",
    asset_class_breakdown: {},
    holdings_detail: [],
    created_at: "2026-04-07T00:00:00Z",
  },
  {
    id: 2,
    user_id: "pb-demo",
    client_id: "client-001",
    client_name: "고객 A",
    snapshot_date: "2026-05-07",
    total_value_krw: "100000000",
    total_pnl_krw: "0",
    asset_class_breakdown: {},
    holdings_detail: [],
    created_at: "2026-05-07T00:00:00Z",
  },
];

function renderPanel(activeKey: KpiEvidenceKey, hiddenHoldingCount = 0) {
  renderWithProviders(
    <KpiEvidencePanel
      activeKey={activeKey}
      clientId="client-001"
      summary={summary}
      snapshots={snapshots}
      hiddenHoldingCount={hiddenHoldingCount}
      panelId="kpi-evidence-panel"
    />,
  );
}

describe("KpiEvidencePanel", () => {
  it("renders total-assets evidence with asset-class breakdown and client link", () => {
    renderPanel("totalAssets");
    expect(screen.getByRole("region", { name: /총자산 근거/ })).toBeInTheDocument();
    expect(screen.getByText("국내주식")).toBeInTheDocument();
    expect(screen.getByText("미국주식")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "고객 상세 보기" })).toHaveAttribute(
      "href",
      "/clients/client-001",
    );
  });

  it("renders daily-change degraded block when holdings snapshots are not comparable", () => {
    renderPanel("dailyChange");
    expect(screen.getByText(/종목별 일간 기여를 산출할 수 없습니다/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "관련 뉴스 보기" })).toHaveAttribute(
      "href",
      "/news?client_id=client-001",
    );
  });

  it("renders period stats for 30-day change", () => {
    renderPanel("periodChange");
    expect(screen.getByText("시작값")).toBeInTheDocument();
    expect(screen.getByText("종료값")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "추이 자세히 보기" })).toHaveAttribute(
      "href",
      "#client-book-asset-trend",
    );
  });

  it("renders hidden holdings warning inside holdings evidence", () => {
    renderPanel("holdings", 2);
    expect(screen.getByText(/2개 보유종목/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "보유 테이블 보기" })).toHaveAttribute(
      "href",
      "/clients/client-001#holdings",
    );
  });

  it("describes concentration risk as asset-class HHI, not a direct recommendation", () => {
    renderPanel("concentration");
    expect(screen.getByText(/자산군별 비중 제곱의 합/)).toBeInTheDocument();
    expect(screen.queryByText(/매수/)).not.toBeInTheDocument();
    expect(screen.queryByText(/매도/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "리밸런싱 검토" })).toHaveAttribute(
      "href",
      "/clients/client-001#rebalance",
    );
  });
});
```

- [ ] **Step 2: Run panel tests to verify they fail**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-evidence-panel.test.tsx
```

Expected: FAIL because `kpi-evidence-panel.tsx` does not exist.

- [ ] **Step 3: Implement the evidence panel component**

Create `frontend/components/dashboard/kpi-evidence-panel.tsx` with these exported types and component shape:

```tsx
"use client";

import { AlertTriangle, ArrowRight, Info } from "lucide-react";
import Link from "next/link";
import type { PortfolioSummary, SnapshotResponse } from "@/lib/api/portfolio";
import { formatKRWCompact, formatPct, signedColorClass } from "@/lib/utils/format";
import {
  buildAssetClassEvidenceRows,
  buildHoldingDistributionRows,
  buildPeriodSnapshotStats,
  buildTopHoldingWeightRows,
  hasComparableHoldingSnapshots,
  hhiFormulaLabel,
} from "./kpi-evidence-utils";

export type KpiEvidenceKey =
  | "totalAssets"
  | "dailyChange"
  | "periodChange"
  | "holdings"
  | "concentration";

interface KpiEvidencePanelProps {
  activeKey: KpiEvidenceKey;
  clientId: string;
  summary: PortfolioSummary;
  snapshots: SnapshotResponse[];
  hiddenHoldingCount: number;
  panelId: string;
}
```

Use these local helpers inside the file:

```tsx
function clientHref(clientId: string, hash = ""): string {
  return `/clients/${encodeURIComponent(clientId)}${hash}`;
}

function clientNewsHref(clientId: string): string {
  return `/news?client_id=${encodeURIComponent(clientId)}`;
}

function EvidenceShell({
  id,
  title,
  value,
  summaryText,
  action,
  children,
}: {
  id: string;
  title: string;
  value: string;
  summaryText: string;
  action: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      role="region"
      aria-labelledby={`${id}-title`}
      className="rounded-xl border bg-card p-4 shadow-sm"
      data-testid="kpi-evidence-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 id={`${id}-title`} className="text-sm font-semibold tracking-tight">
            {title}
          </h3>
          <p className="mt-1 text-2xl font-bold tabular-nums text-foreground">
            {value}
          </p>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            {summaryText}
          </p>
        </div>
        <div className="shrink-0">{action}</div>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        {children}
      </div>
    </section>
  );
}

function EvidenceAction({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-semibold text-primary transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {children}
      <ArrowRight className="h-4 w-4" aria-hidden="true" />
    </Link>
  );
}

function EvidenceBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0 rounded-lg border bg-muted/20 p-3">
      <h4 className="text-xs font-semibold text-muted-foreground">{title}</h4>
      <div className="mt-3 min-w-0">{children}</div>
    </div>
  );
}

function DegradedBlock({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>{children}</p>
    </div>
  );
}

function SourceDetails({ children }: { children: React.ReactNode }) {
  return (
    <details className="rounded-md border bg-background p-3 text-xs text-muted-foreground">
      <summary className="cursor-pointer font-semibold text-foreground">
        계산 기준과 출처
      </summary>
      <div className="mt-2 leading-5">{children}</div>
    </details>
  );
}
```

Implement each KPI branch inside `KpiEvidencePanel` with deterministic content:

```tsx
export function KpiEvidencePanel({
  activeKey,
  clientId,
  summary,
  snapshots,
  hiddenHoldingCount,
  panelId,
}: KpiEvidencePanelProps) {
  const totalValue = Number(summary.total_value_krw);
  const topHoldings = buildTopHoldingWeightRows(summary.holdings, totalValue, 5);

  if (activeKey === "totalAssets") {
    const rows = buildAssetClassEvidenceRows(summary);
    return (
      <EvidenceShell
        id={panelId}
        title="총자산 근거"
        value={formatKRWCompact(summary.total_value_krw)}
        summaryText="현재 보유 종목의 KRW 환산 평가금액을 합산한 값입니다."
        action={<EvidenceAction href={clientHref(clientId)}>고객 상세 보기</EvidenceAction>}
      >
        <EvidenceBlock title="자산군별 평가금액">
          <div className="space-y-2">
            {rows.map((row) => (
              <div key={row.key} className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-3 text-sm">
                <span className="min-w-0 truncate">{row.label}</span>
                <span className="tabular-nums">{formatKRWCompact(row.valueKrw)}</span>
                <span className="tabular-nums text-muted-foreground">{formatPct(row.ratio * 100)}</span>
              </div>
            ))}
          </div>
        </EvidenceBlock>
        <EvidenceBlock title="상위 보유 종목">
          <HoldingWeightList rows={topHoldings} />
        </EvidenceBlock>
        <div className="lg:col-span-2">
          <SourceDetails>
            Source fields: summary.total_value_krw, summary.asset_class_breakdown, summary.holdings.
          </SourceDetails>
        </div>
      </EvidenceShell>
    );
  }

  if (activeKey === "dailyChange") {
    const comparable = hasComparableHoldingSnapshots(snapshots);
    return (
      <EvidenceShell
        id={panelId}
        title="일간 변동 근거"
        value={formatPct(summary.daily_change_pct, { signed: true })}
        summaryText={`${formatKRWCompact(summary.daily_change_krw)}의 일간 평가금액 변화입니다.`}
        action={<EvidenceAction href={clientNewsHref(clientId)}>관련 뉴스 보기</EvidenceAction>}
      >
        <EvidenceBlock title="종목별 일간 기여">
          {comparable ? (
            <DegradedBlock>종목별 일간 기여 UI는 비교 가능한 스냅샷 필드 연결 후 표시합니다.</DegradedBlock>
          ) : (
            <DegradedBlock>현재 데이터로 종목별 일간 기여를 산출할 수 없습니다.</DegradedBlock>
          )}
        </EvidenceBlock>
        <EvidenceBlock title="자산군 요약">
          <p className={`text-sm font-semibold tabular-nums ${signedColorClass(summary.daily_change_krw)}`}>
            {formatPct(summary.daily_change_pct, { signed: true })} / {formatKRWCompact(summary.daily_change_krw)}
          </p>
        </EvidenceBlock>
        <div className="lg:col-span-2">
          <SourceDetails>
            Source fields: summary.daily_change_krw, summary.daily_change_pct, snapshots.holdings_detail.
          </SourceDetails>
        </div>
      </EvidenceShell>
    );
  }

  if (activeKey === "periodChange") {
    const stats = buildPeriodSnapshotStats(snapshots);
    return (
      <EvidenceShell
        id={panelId}
        title="30일 변동 근거"
        value={formatPct(summary.period_change_pct, { signed: true })}
        summaryText={`${summary.period_days}일 기준 포트폴리오 평가금액 변화입니다.`}
        action={<EvidenceAction href="#client-book-asset-trend">추이 자세히 보기</EvidenceAction>}
      >
        <EvidenceBlock title="기간 추이 요약">
          {stats ? (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <MetricTerm label="시작값" value={formatKRWCompact(stats.startValueKrw)} />
              <MetricTerm label="종료값" value={formatKRWCompact(stats.endValueKrw)} />
              <MetricTerm label="최고" value={formatKRWCompact(stats.highValueKrw)} />
              <MetricTerm label="최저" value={formatKRWCompact(stats.lowValueKrw)} />
            </dl>
          ) : (
            <DegradedBlock>기간 추이를 계산할 스냅샷이 2개 이상 필요합니다.</DegradedBlock>
          )}
        </EvidenceBlock>
        <EvidenceBlock title="기간 비교">
          <DegradedBlock>7일/90일 비교는 해당 기간 스냅샷이 충분할 때 표시합니다.</DegradedBlock>
        </EvidenceBlock>
        <div className="lg:col-span-2">
          <SourceDetails>
            Source fields: summary.period_change_pct, summary.period_days, snapshots.
          </SourceDetails>
        </div>
      </EvidenceShell>
    );
  }

  if (activeKey === "holdings") {
    const distribution = buildHoldingDistributionRows(summary.holdings);
    return (
      <EvidenceShell
        id={panelId}
        title="보유 종목 근거"
        value={`${summary.holdings_count}개`}
        summaryText="현재 고객 포트폴리오에 등록된 보유 종목 수입니다."
        action={<EvidenceAction href={clientHref(clientId, "#holdings")}>보유 테이블 보기</EvidenceAction>}
      >
        <EvidenceBlock title="자산군별 종목 수">
          <div className="space-y-2">
            {distribution.map((row) => (
              <div key={row.key} className="flex justify-between gap-3 text-sm">
                <span>{row.label}</span>
                <span className="font-semibold tabular-nums">{row.count}개</span>
              </div>
            ))}
          </div>
        </EvidenceBlock>
        <EvidenceBlock title="상위 보유 종목">
          {hiddenHoldingCount > 0 ? (
            <DegradedBlock>가격 또는 통화 데이터가 안전하게 표시되지 않아 {hiddenHoldingCount}개 보유종목을 숨겼습니다.</DegradedBlock>
          ) : null}
          <HoldingWeightList rows={topHoldings} />
        </EvidenceBlock>
        <div className="lg:col-span-2">
          <SourceDetails>
            Source fields: summary.holdings_count, summary.holdings, display-safety filtering.
          </SourceDetails>
        </div>
      </EvidenceShell>
    );
  }

  return (
    <EvidenceShell
      id={panelId}
      title="집중도 리스크 근거"
      value={formatPct(summary.risk_score_pct)}
      summaryText="현재 점수는 자산군 쏠림 정도를 기준으로 계산됩니다."
      action={<EvidenceAction href={clientHref(clientId, "#rebalance")}>리밸런싱 검토</EvidenceAction>}
    >
      <EvidenceBlock title="자산군 HHI 산식">
        {totalValue > 0 && Object.keys(summary.asset_class_breakdown).length > 0 ? (
          <p className="text-sm text-muted-foreground">{hhiFormulaLabel}</p>
        ) : (
          <DegradedBlock>총자산 또는 자산군 비중이 없어 집중도 산식을 설명할 수 없습니다.</DegradedBlock>
        )}
      </EvidenceBlock>
      <EvidenceBlock title="상위 보유 종목 참고">
        <HoldingWeightList rows={topHoldings} />
      </EvidenceBlock>
      <div className="lg:col-span-2">
        <SourceDetails>
          Source fields: summary.risk_score_pct, summary.asset_class_breakdown, summary.total_value_krw, summary.holdings. 이 점수는 손실 확률이나 직접 매매 권고가 아닙니다.
        </SourceDetails>
      </div>
    </EvidenceShell>
  );
}
```

Add these small render helpers at the bottom of the file:

```tsx
function HoldingWeightList({
  rows,
}: {
  rows: Array<{ id: number; market: string; code: string; valueKrw: number; weightPct: number; pnlPct: number }>;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">표시 가능한 보유 종목이 없습니다.</p>;
  }

  return (
    <div className="min-w-0 overflow-x-auto">
      <div className="min-w-[360px] space-y-2">
        {rows.map((row) => (
          <div key={row.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-3 text-sm">
            <span className="min-w-0 truncate font-medium">
              {row.market.toUpperCase()} · {row.code}
            </span>
            <span className="tabular-nums">{formatKRWCompact(row.valueKrw)}</span>
            <span className="tabular-nums text-muted-foreground">{formatPct(row.weightPct)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricTerm({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
```

- [ ] **Step 4: Run panel and helper tests**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-evidence-utils.test.ts components/dashboard/kpi-evidence-panel.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit panel component work**

```bash
git add frontend/components/dashboard/kpi-evidence-panel.tsx frontend/components/dashboard/kpi-evidence-panel.test.tsx
git commit -m "구현: 고객장부 KPI 근거 패널 추가"
```

---

### Task 4: Wire The Panel Into Customer Book Dashboard

**Files:**
- Modify: `frontend/components/dashboard/dashboard-home.tsx`
- Modify: `frontend/components/dashboard/dashboard-home.test.tsx`
- Modify: `frontend/components/clients/client-workspace.tsx`

- [ ] **Step 1: Add failing dashboard integration tests**

Append these tests inside `frontend/components/dashboard/dashboard-home.test.tsx`:

```tsx
import { fireEvent, within } from "@testing-library/react";
```

If `fireEvent` or `within` are already imported, merge them into the existing import.

Add tests:

```tsx
describe("SelectedClientDashboard KPI evidence", () => {
  beforeEach(() => {
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getSnapshots.mockReset();
    portfolioMocks.getPortfolioSummary.mockResolvedValue(SUMMARY);
    portfolioMocks.getSnapshots.mockResolvedValue([
      {
        id: 1,
        user_id: "pb-demo",
        client_id: "client-001",
        client_name: "고객 A",
        snapshot_date: "2026-04-07",
        total_value_krw: "90000000",
        total_pnl_krw: "0",
        asset_class_breakdown: {},
        holdings_detail: [],
        created_at: "2026-04-07T00:00:00Z",
      },
      {
        id: 2,
        user_id: "pb-demo",
        client_id: "client-001",
        client_name: "고객 A",
        snapshot_date: "2026-05-07",
        total_value_krw: "100000000",
        total_pnl_krw: "0",
        asset_class_breakdown: {},
        holdings_detail: [],
        created_at: "2026-05-07T00:00:00Z",
      },
    ]);
  });

  it("opens total-assets evidence by default in customer-book mode", async () => {
    renderWithProviders(
      <SelectedClientDashboard clientId="client-001" clientName="고객 A" variant="clientBook" />,
      { withQuery: true },
    );

    expect(await screen.findByRole("region", { name: /총자산 근거/ })).toBeInTheDocument();
    const totalCard = screen.getByRole("button", { name: /총자산/ });
    expect(totalCard).toHaveAttribute("aria-expanded", "true");
  });

  it("switches evidence panel when a KPI card is clicked", async () => {
    renderWithProviders(
      <SelectedClientDashboard clientId="client-001" clientName="고객 A" variant="clientBook" />,
      { withQuery: true },
    );

    await screen.findByRole("region", { name: /총자산 근거/ });
    fireEvent.click(screen.getByRole("button", { name: /일간 변동/ }));
    expect(screen.getByRole("region", { name: /일간 변동 근거/ })).toBeInTheDocument();
    expect(screen.getByText(/종목별 일간 기여를 산출할 수 없습니다/)).toBeInTheDocument();
  });

  it("does not render KPI evidence controls in full dashboard mode", async () => {
    renderWithProviders(<SelectedClientDashboard clientId="client-001" />, {
      withQuery: true,
    });

    expect(await screen.findByTestId("section-risk")).toBeInTheDocument();
    expect(screen.queryByTestId("kpi-evidence-panel")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /총자산/ })).not.toBeInTheDocument();
  });

  it("keeps evidence actions scoped to the selected client", async () => {
    renderWithProviders(
      <SelectedClientDashboard clientId="client-001" clientName="고객 A" variant="clientBook" />,
      { withQuery: true },
    );

    const panel = await screen.findByTestId("kpi-evidence-panel");
    expect(within(panel).getByRole("link", { name: "고객 상세 보기" })).toHaveAttribute(
      "href",
      "/clients/client-001",
    );

    fireEvent.click(screen.getByRole("button", { name: /집중도 리스크/ }));
    expect(screen.getByRole("link", { name: "리밸런싱 검토" })).toHaveAttribute(
      "href",
      "/clients/client-001#rebalance",
    );
  });
});
```

- [ ] **Step 2: Run dashboard tests to verify they fail**

Run:

```bash
cd frontend && npm run test -- components/dashboard/dashboard-home.test.tsx
```

Expected: FAIL because dashboard wiring is missing.

- [ ] **Step 3: Wire selected KPI state and panel into dashboard-home**

Modify imports in `frontend/components/dashboard/dashboard-home.tsx`:

```tsx
import {
  KpiEvidencePanel,
  type KpiEvidenceKey,
} from "@/components/dashboard/kpi-evidence-panel";
```

Inside `SelectedClientDashboard`, add after `const [period, setPeriod] = useState<PeriodKey>("1M");`:

```tsx
const [activeEvidenceKey, setActiveEvidenceKey] =
  useState<KpiEvidenceKey>("totalAssets");
const evidencePanelId = "client-book-kpi-evidence-panel";
```

For each customer-book KPI card, pass interactive props only when `isClientBookPreview` is true:

```tsx
onClick={isClientBookPreview ? () => setActiveEvidenceKey("totalAssets") : undefined}
selected={isClientBookPreview && activeEvidenceKey === "totalAssets"}
controlsId={isClientBookPreview ? evidencePanelId : undefined}
```

Use these keys:

- Total assets: `"totalAssets"`
- Daily change: `"dailyChange"`
- 30-day change: `"periodChange"`
- Holdings count: `"holdings"`
- Concentration risk: `"concentration"`

Render the panel immediately after the KPI `<section>`:

```tsx
{isClientBookPreview && summary ? (
  <KpiEvidencePanel
    activeKey={activeEvidenceKey}
    clientId={clientId}
    summary={summary}
    snapshots={snapshotsQuery.data ?? []}
    hiddenHoldingCount={hiddenHoldingCount}
    panelId={evidencePanelId}
  />
) : null}
```

Add the trend section id to the first `SectionCard` wrapper by moving the span class to a wrapper:

```tsx
<div
  id={isClientBookPreview ? "client-book-asset-trend" : undefined}
  className={
    isClientBookPreview
      ? "xl:col-span-1 2xl:col-span-5"
      : "lg:col-span-5"
  }
>
  <SectionCard
    title={t("dashboard.assetTrend")}
    testId="section-networth"
    action={
      isClientBookPreview ? (
        <PeriodTabs value={period} onChange={setPeriod} />
      ) : (
        <span className="text-xs text-muted-foreground">
          {PERIOD_DAYS[period]}일
        </span>
      )
    }
  >
    {snapshotsQuery.isLoading ? (
      <Skeleton className="h-56 w-full" />
    ) : (
      <NetworthChart snapshots={snapshotsQuery.data ?? []} />
    )}
  </SectionCard>
</div>
```

Remove the old conditional grid-span `className` prop from this `SectionCard` because the wrapper now owns the grid column span.

- [ ] **Step 4: Add stable workspace anchors**

Modify `frontend/components/clients/client-workspace.tsx`.

For the holdings section, add `id="holdings"` to the existing `SectionCard` wrapper by wrapping it:

```tsx
<div id="holdings" className="lg:col-span-8">
  <SectionCard
    title={t("portfolio.holdingsOverview")}
    testId="portfolio-section-holdings"
  >
    {hiddenHoldingCount > 0 && (
      <p className="mb-3 text-xs text-muted-foreground">
        가격 또는 통화 데이터가 안전하게 표시되지 않아 {hiddenHoldingCount}개 보유종목을 숨겼습니다.
      </p>
    )}
    <HoldingsTable holdings={displayHoldings} />
  </SectionCard>
</div>
```

For the rebalance section, add `id="rebalance"` to the existing section:

```tsx
<section
  id="rebalance"
  aria-labelledby="portfolio-rebalance-title"
  className="space-y-4"
  data-testid="portfolio-section-rebalance"
>
```

- [ ] **Step 5: Run dashboard and panel tests**

Run:

```bash
cd frontend && npm run test -- components/dashboard/dashboard-home.test.tsx components/dashboard/kpi-evidence-panel.test.tsx components/dashboard/kpi-card.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit dashboard wiring**

```bash
git add frontend/components/dashboard/dashboard-home.tsx frontend/components/dashboard/dashboard-home.test.tsx frontend/components/clients/client-workspace.tsx
git commit -m "구현: 고객장부 KPI 근거 패널 연결"
```

---

### Task 5: Final Verification And Visual Check

**Files:**
- No planned source changes unless verification exposes a defect.

- [ ] **Step 1: Run focused frontend unit tests**

Run:

```bash
cd frontend && npm run test -- components/dashboard/kpi-evidence-utils.test.ts components/dashboard/kpi-evidence-panel.test.tsx components/dashboard/kpi-card.test.tsx components/dashboard/dashboard-home.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run frontend typecheck**

Run:

```bash
cd frontend && npm run typecheck
```

Expected: PASS.

- [ ] **Step 3: Run frontend lint**

Run:

```bash
cd frontend && npm run lint
```

Expected: PASS or only pre-existing unrelated warnings. If new lint errors appear in edited files, fix them before continuing.

- [ ] **Step 4: Start local frontend for browser verification**

Run:

```bash
cd frontend && npm run dev
```

Expected: local Next.js dev server URL, usually `http://localhost:3000`.

- [ ] **Step 5: Use browser-use for routed customer-book smoke**

Open `/` in the in-app browser. Verify:

- Customer list loads.
- Selected customer dashboard shows five KPI cards.
- Total-assets evidence panel is visible by default.
- Clicking daily change, 30-day change, holdings, and concentration changes the panel.
- Text does not overlap at desktop width.
- In responsive/mobile width, KPI cards and panel text do not overlap.
- Degraded daily-change block is visible when per-holding daily contribution cannot be computed.
- Concentration-risk panel says asset-class HHI and does not contain buy/sell recommendation language.

- [ ] **Step 6: Commit verification fixes if any**

If Step 5 required source changes:

```bash
git add <changed-files>
git commit -m "수정: KPI 근거 패널 시각 검증 보완"
```

If Step 5 required no source changes, do not create an empty commit.
