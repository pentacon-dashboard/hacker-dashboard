import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { SelectedClientDashboard } from "./dashboard-home";

const portfolioMocks = vi.hoisted(() => ({
  getPortfolioSummary: vi.fn(),
  getSnapshots: vi.fn(),
}));

const watchlistMocks = vi.hoisted(() => ({
  getAlerts: vi.fn(),
}));

const newsMocks = vi.hoisted(() => ({
  searchNews: vi.fn(),
}));

const networthChartMocks = vi.hoisted(() => ({
  render: vi.fn(),
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

vi.mock("@/lib/api/watchlist", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/watchlist")>(
    "@/lib/api/watchlist",
  );
  return {
    ...actual,
    getAlerts: watchlistMocks.getAlerts,
  };
});

vi.mock("@/lib/api/news", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/news")>(
    "@/lib/api/news",
  );
  return {
    ...actual,
    searchNews: newsMocks.searchNews,
  };
});

vi.mock("@/components/portfolio/networth-chart", () => ({
  NetworthChart: (props: { range?: { from?: string; to?: string } }) => {
    networthChartMocks.render(props);
    return (
      <div
        data-testid="mock-networth-chart"
        data-from={props.range?.from}
        data-to={props.range?.to}
      />
    );
  },
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

function formatDate(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function expectedRange(days: number) {
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - days);
  return { from: formatDate(from), to: formatDate(to) };
}

describe("SelectedClientDashboard monitoring links", () => {
  beforeEach(() => {
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getSnapshots.mockReset();
    watchlistMocks.getAlerts.mockReset();
    newsMocks.searchNews.mockReset();
    networthChartMocks.render.mockClear();
    portfolioMocks.getPortfolioSummary.mockResolvedValue(SUMMARY);
    portfolioMocks.getSnapshots.mockResolvedValue([]);
    watchlistMocks.getAlerts.mockResolvedValue([
      {
        id: 1,
        user_id: "pb-demo",
        symbol: "005930",
        market: "naver_kr",
        direction: "below",
        threshold: "60000",
        enabled: true,
        created_at: "2026-05-01T00:00:00Z",
      },
      {
        id: 2,
        user_id: "pb-demo",
        symbol: "AAPL",
        market: "yahoo",
        direction: "above",
        threshold: "200",
        enabled: true,
        created_at: "2026-05-02T00:00:00Z",
      },
    ]);
    newsMocks.searchNews.mockResolvedValue([
      {
        doc_id: 1,
        chunk_id: 1,
        source_url: "https://example.com/a",
        title: "news a",
      },
      {
        doc_id: 2,
        chunk_id: 1,
        source_url: "https://example.com/b",
        title: "news b",
      },
      {
        doc_id: 3,
        chunk_id: 1,
        source_url: "https://example.com/c",
        title: "news c",
      },
      {
        doc_id: 4,
        chunk_id: 1,
        source_url: "https://example.com/d",
        title: "news d",
      },
    ]);
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

  it("uses the same counts as the linked monitoring detail pages", async () => {
    renderWithProviders(
      <SelectedClientDashboard
        clientId="client-001"
        clientName="고객 A"
        variant="clientBook"
      />,
      { withQuery: true },
    );

    const attentionCard = await screen.findByRole("link", { name: /주의 종목/ });
    const alertCard = await screen.findByRole("link", { name: /가격 알림/ });
    const newsCard = await screen.findByRole("link", { name: /관련 뉴스/ });

    expect(within(attentionCard).getByText("1")).toBeInTheDocument();
    expect(await within(alertCard).findByText("2")).toBeInTheDocument();
    expect(await within(newsCard).findByText("4")).toBeInTheDocument();
    expect(watchlistMocks.getAlerts).toHaveBeenCalledOnce();
    expect(newsMocks.searchNews).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "005930",
        symbols: ["005930"],
        k: 8,
      }),
    );
  });
});

describe("SelectedClientDashboard KPI evidence", () => {
  beforeEach(() => {
    portfolioMocks.getPortfolioSummary.mockReset();
    portfolioMocks.getSnapshots.mockReset();
    watchlistMocks.getAlerts.mockReset();
    newsMocks.searchNews.mockReset();
    networthChartMocks.render.mockClear();
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
    watchlistMocks.getAlerts.mockResolvedValue([]);
    newsMocks.searchNews.mockResolvedValue([]);
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

  it("updates networth chart requests and range when the period tab changes", async () => {
    renderWithProviders(
      <SelectedClientDashboard clientId="client-001" clientName="고객 A" variant="clientBook" />,
      { withQuery: true },
    );

    expect(await screen.findByTestId("mock-networth-chart")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "1Y" }));

    const oneYearRange = expectedRange(365);
    await waitFor(() =>
      expect(portfolioMocks.getPortfolioSummary).toHaveBeenCalledWith(365, "client-001"),
    );
    await waitFor(() =>
      expect(portfolioMocks.getSnapshots).toHaveBeenCalledWith(
        oneYearRange.from,
        oneYearRange.to,
        "client-001",
      ),
    );
    await waitFor(() =>
      expect(screen.getByTestId("mock-networth-chart")).toHaveAttribute(
        "data-from",
        oneYearRange.from,
      ),
    );
    expect(screen.getByTestId("mock-networth-chart")).toHaveAttribute(
      "data-to",
      oneYearRange.to,
    );
  });

  it("does not render KPI evidence action buttons in customer-book mode", async () => {
    renderWithProviders(
      <SelectedClientDashboard clientId="client-001" clientName="고객 A" variant="clientBook" />,
      { withQuery: true },
    );

    const panel = await screen.findByTestId("kpi-evidence-panel");
    expect(within(panel).queryByRole("link", { name: "고객 상세 보기" })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "고객 상세 보기" })).not.toBeInTheDocument();
    expect(within(panel).queryByText("고객 상세 보기")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /집중도 리스크/ }));
    expect(screen.queryByRole("link", { name: "리밸런싱 검토" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "리밸런싱 검토" })).not.toBeInTheDocument();
    expect(screen.queryByText("리밸런싱 검토")).not.toBeInTheDocument();
  });
});
