import { describe, expect, it } from "vitest";
import type {
  HoldingDetail,
  PortfolioSummary,
  SnapshotResponse,
} from "@/lib/api/portfolio";
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
    holding({
      id: 1,
      market: "naver_kr",
      code: "005930",
      value_krw: "70000000",
    }),
    holding({
      id: 2,
      market: "nasdaq",
      code: "AAPL",
      currency: "USD",
      value_krw: "30000000",
    }),
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

  it("sorts top holdings by value, slices by limit, and guards non-positive totals", () => {
    const holdings = [
      holding({ id: 3, market: "nyse", code: "MSFT", value_krw: "10000000" }),
      holding({ id: 1, market: "naver_kr", code: "005930", value_krw: "70000000" }),
      holding({ id: 2, market: "nasdaq", code: "AAPL", value_krw: "30000000" }),
    ];

    expect(buildTopHoldingWeightRows(holdings, 100000000, 2)).toMatchObject([
      { code: "005930", valueKrw: 70000000, weightPct: 70 },
      { code: "AAPL", valueKrw: 30000000, weightPct: 30 },
    ]);
    expect(buildTopHoldingWeightRows(holdings, 100000000, 2)).toHaveLength(2);
    expect(buildTopHoldingWeightRows(holdings, 0, 1)).toMatchObject([
      { code: "005930", weightPct: 0 },
    ]);
  });

  it("classifies markets using backend-compatible asset classes", () => {
    expect(classifyMarketAssetClass("upbit")).toBe("crypto");
    expect(classifyMarketAssetClass("binance")).toBe("crypto");
    expect(classifyMarketAssetClass("yahoo")).toBe("stock_us");
    expect(classifyMarketAssetClass("nasdaq")).toBe("stock_us");
    expect(classifyMarketAssetClass("nyse")).toBe("stock_us");
    expect(classifyMarketAssetClass("naver_kr")).toBe("stock_kr");
    expect(classifyMarketAssetClass("krx")).toBe("stock_kr");
    expect(classifyMarketAssetClass("unknown")).toBe("other");
  });

  it("builds holding distribution rows by asset class", () => {
    expect(buildHoldingDistributionRows(summary.holdings)).toEqual([
      { key: "stock_kr", label: "국내주식", count: 1 },
      { key: "stock_us", label: "미국주식", count: 1 },
    ]);
  });

  it("builds snapshot period stats by sorting snapshot dates", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(3, "2026-05-07", "100000000"),
        snapshot(1, "2026-04-07", "90000000"),
        snapshot(2, "2026-04-20", "110000000"),
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

  it("returns null snapshot stats when the start value is zero", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "0"),
        snapshot(2, "2026-05-07", "100000000"),
      ]),
    ).toBeNull();
  });

  it("returns null snapshot stats when the start value is negative", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "-1000000"),
        snapshot(2, "2026-05-07", "100000000"),
      ]),
    ).toBeNull();
  });

  it("returns null snapshot stats when the end value is zero", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "90000000"),
        snapshot(2, "2026-05-07", "0"),
      ]),
    ).toBeNull();
  });

  it("returns null snapshot stats when the end value is negative", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "90000000"),
        snapshot(2, "2026-05-07", "-1000000"),
      ]),
    ).toBeNull();
  });

  it("returns null snapshot stats when the start or end value is invalid", () => {
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "not-a-number"),
        snapshot(2, "2026-05-07", "100000000"),
      ]),
    ).toBeNull();
    expect(
      buildPeriodSnapshotStats([
        snapshot(1, "2026-04-07", "90000000"),
        snapshot(2, "2026-05-07", "not-a-number"),
      ]),
    ).toBeNull();
  });

  it("requires aligned holdings_detail for comparable holding snapshots", () => {
    const comparable = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "10" }],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "12" }],
      },
    ];
    const notComparable = [
      { ...snapshot(1, "2026-05-06", "90000000"), holdings_detail: [] },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "12" }],
      },
    ];
    expect(hasComparableHoldingSnapshots(comparable)).toBe(true);
    expect(hasComparableHoldingSnapshots(notComparable)).toBe(false);
  });

  it("requires equivalent first and last holding identity sets", () => {
    const equivalent = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "10" },
          { market: "nyse", code: "MSFT", value_krw: "20" },
        ],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [
          { market: "nyse", code: "MSFT", value_krw: "22" },
          { market: "nasdaq", code: "AAPL", value_krw: "12" },
        ],
      },
    ];
    const partiallyMismatched = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "10" },
          { market: "nyse", code: "MSFT", value_krw: "20" },
        ],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "12" },
          { market: "nasdaq", code: "GOOG", value_krw: "30" },
        ],
      },
    ];

    expect(hasComparableHoldingSnapshots(equivalent)).toBe(true);
    expect(hasComparableHoldingSnapshots(partiallyMismatched)).toBe(false);
  });

  it("rejects comparable holding snapshots when either side has an invalid identity", () => {
    const invalidFirstSide = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "10" },
          { market: "nyse", code: "MSFT", value_krw: "not-a-number" },
        ],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "12" },
          { market: "nyse", code: "MSFT", value_krw: "22" },
        ],
      },
    ];
    const invalidLastSide = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "10" },
          { market: "nyse", code: "MSFT", value_krw: "20" },
        ],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "12" },
          { market: "nyse", code: "MSFT", value_krw: "not-a-number" },
        ],
      },
    ];

    expect(hasComparableHoldingSnapshots(invalidFirstSide)).toBe(false);
    expect(hasComparableHoldingSnapshots(invalidLastSide)).toBe(false);
  });

  it("rejects comparable holding snapshots without shared numeric identities", () => {
    const noSharedIdentity = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "10" }],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [{ market: "nyse", code: "MSFT", value_krw: "12" }],
      },
    ];
    const nonNumericValue = [
      {
        ...snapshot(1, "2026-05-06", "90000000"),
        holdings_detail: [
          { market: "nasdaq", code: "AAPL", value_krw: "not-a-number" },
        ],
      },
      {
        ...snapshot(2, "2026-05-07", "100000000"),
        holdings_detail: [{ market: "nasdaq", code: "AAPL", value_krw: "12" }],
      },
    ];

    expect(hasComparableHoldingSnapshots(noSharedIdentity)).toBe(false);
    expect(hasComparableHoldingSnapshots(nonNumericValue)).toBe(false);
  });

  it("uses asset-class HHI language for concentration score", () => {
    expect(hhiFormulaLabel).toContain("자산군");
    expect(hhiFormulaLabel).toContain("HHI");
  });
});
