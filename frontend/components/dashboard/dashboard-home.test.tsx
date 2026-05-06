import { fireEvent, screen, within } from "@testing-library/react";
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
