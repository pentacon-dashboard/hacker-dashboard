import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { NewsPageClient } from "./news-page-client";

const nav = vi.hoisted(() => ({
  search: "",
}));

const portfolioMocks = vi.hoisted(() => ({
  getPortfolioSummary: vi.fn(),
}));

const newsPanelMock = vi.hoisted(() => ({
  props: vi.fn(),
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

vi.mock("@/components/dashboard/news-panel", () => ({
  NewsPanel: (props: { symbols: string[]; query?: string; limit?: number }) => {
    newsPanelMock.props(props);
    return <div data-testid="mock-news-panel">{props.symbols.join(",")}</div>;
  },
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
    {
      id: 2,
      market: "yahoo",
      code: "NVDA",
      quantity: "2",
      avg_cost: "700",
      currency: "USD",
      current_price: "720",
      current_price_krw: "990000",
      value_krw: "1980000",
      cost_krw: "1800000",
      pnl_krw: "180000",
      pnl_pct: "10.00",
    },
  ],
  holdings_count: 2,
  worst_asset_pct: "-2.50",
  risk_score_pct: "42.00",
  period_change_pct: "2.40",
  period_days: 30,
  dimension_breakdown: [],
  win_rate_pct: "50.00",
};

describe("NewsPageClient", () => {
  beforeEach(() => {
    nav.search = "";
    newsPanelMock.props.mockReset();
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getPortfolioSummary.mockResolvedValue(SUMMARY);
  });

  it("loads client holdings and passes their symbols to NewsPanel", async () => {
    nav.search = "client_id=client-001";
    renderWithProviders(<NewsPageClient />, { withQuery: true });

    expect(await screen.findByTestId("mock-news-panel")).toHaveTextContent(
      "005930,NVDA",
    );
    expect(portfolioMocks.getPortfolioSummary).toHaveBeenCalledWith(30, "client-001");
    await waitFor(() => {
      expect(newsPanelMock.props).toHaveBeenCalledWith(
        expect.objectContaining({
          symbols: ["005930", "NVDA"],
          query: "005930 OR NVDA",
          limit: 8,
        }),
      );
    });
  });
});
