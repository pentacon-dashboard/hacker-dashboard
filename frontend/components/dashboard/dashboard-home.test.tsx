import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { SelectedClientDashboard } from "./dashboard-home";

const portfolioMocks = vi.hoisted(() => ({
  getPortfolioSummary: vi.fn(),
  getSnapshots: vi.fn(),
}));

vi.mock("@/lib/api/portfolio", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/portfolio")>(
    "@/lib/api/portfolio",
  );
  return {
    ...actual,
    getPortfolioSummary: portfolioMocks.getPortfolioSummary,
    getSnapshots: portfolioMocks.getSnapshots,
  };
});

vi.mock("@/components/portfolio/networth-chart", () => ({
  NetworthChart: () => <div data-testid="mock-networth-chart" />,
}));

vi.mock("@/components/dashboard/allocation-breakdown", () => ({
  AllocationBreakdown: () => <div data-testid="mock-allocation-breakdown" />,
}));

vi.mock("@/components/dashboard/top-holdings-table", () => ({
  TopHoldingsTable: () => <div data-testid="mock-top-holdings-table" />,
}));

const SUMMARY = {
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
  holdings: [
    {
      id: 1,
      market: "naver_kr",
      code: "005930",
      quantity: "10",
      avg_cost: "70000",
      currency: "KRW",
      current_price: "68000",
      current_price_krw: "68000",
      value_krw: "25000000",
      cost_krw: "700000",
      pnl_krw: "-20000",
      pnl_pct: "-2.50",
    },
  ],
  holdings_count: 1,
  worst_asset_pct: "-2.50",
  risk_score_pct: "42.00",
  period_change_pct: "2.40",
  period_days: 30,
  dimension_breakdown: [],
  win_rate_pct: "0.00",
};

describe("SelectedClientDashboard monitoring links", () => {
  beforeEach(() => {
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getSnapshots.mockReset();
    portfolioMocks.getPortfolioSummary.mockResolvedValue(SUMMARY);
    portfolioMocks.getSnapshots.mockResolvedValue([]);
  });

  it("links client-book monitoring cards to watchlist alerts and client news routes", async () => {
    renderWithProviders(
      <SelectedClientDashboard
        clientId="client-001"
        clientName="고객 A"
        variant="clientBook"
      />,
      { withQuery: true },
    );

    expect(await screen.findByTestId("client-monitoring-signals")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /주의 종목/ })).toHaveAttribute(
      "href",
      "/watchlist?client_id=client-001&filter=attention",
    );
    expect(screen.getByRole("link", { name: /가격 알림/ })).toHaveAttribute(
      "href",
      "/watchlist?client_id=client-001&tab=alerts",
    );
    expect(screen.getByRole("link", { name: /관련 뉴스/ })).toHaveAttribute(
      "href",
      "/news?client_id=client-001",
    );
  });
});
