import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { WatchlistPageClient } from "./watchlist-page-client";

const nav = vi.hoisted(() => ({
  search: "",
}));

const portfolioMocks = vi.hoisted(() => ({
  getPortfolioSummary: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(nav.search),
}));

vi.mock("@/lib/api/portfolio", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/portfolio")>(
    "@/lib/api/portfolio",
  );
  return {
    ...actual,
    getPortfolioSummary: portfolioMocks.getPortfolioSummary,
  };
});

vi.mock("@/components/watchlist/watchlist-table", () => ({
  WatchlistTable: () => <div data-testid="mock-watchlist-table" />,
}));

vi.mock("@/components/watchlist/alert-settings-card", () => ({
  AlertSettingsCard: () => <div data-testid="mock-alert-settings-card" />,
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
  asset_class_breakdown: { stock_kr: "1.0" },
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

describe("WatchlistPageClient", () => {
  beforeEach(() => {
    nav.search = "";
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getPortfolioSummary.mockResolvedValue(SUMMARY);
  });

  it("shows client attention holdings when filter=attention is present", async () => {
    nav.search = "client_id=client-001&filter=attention";
    renderWithProviders(<WatchlistPageClient />, { withQuery: true });

    expect(await screen.findByTestId("attention-holdings-panel")).toBeInTheDocument();
    expect(portfolioMocks.getPortfolioSummary).toHaveBeenCalledWith(30, "client-001");
    expect(screen.getByRole("link", { name: /삼성전자/ })).toHaveAttribute(
      "href",
      "/symbol/naver_kr/005930",
    );
  });

  it("opens the alert settings surface when tab=alerts is present", async () => {
    nav.search = "client_id=client-001&tab=alerts";
    renderWithProviders(<WatchlistPageClient />, { withQuery: true });

    expect(await screen.findByTestId("mock-alert-settings-card")).toBeInTheDocument();
    expect(screen.getByTestId("mock-watchlist-table")).toBeInTheDocument();
  });
});
