import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import type { PortfolioSummary, SnapshotResponse } from "@/lib/api/portfolio";
import { KpiEvidencePanel, type KpiEvidenceKey } from "./kpi-evidence-panel";
import { hhiFormulaLabel } from "./kpi-evidence-utils";

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

function renderPanel(
  activeKey: KpiEvidenceKey,
  hiddenHoldingCount = 0,
  panelSnapshots: SnapshotResponse[] = snapshots,
  panelSummary: PortfolioSummary = summary,
) {
  return renderWithProviders(
    <KpiEvidencePanel
      activeKey={activeKey}
      clientId="client-001"
      summary={panelSummary}
      snapshots={panelSnapshots}
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

  it("renders degraded period comparison text when snapshots are insufficient", () => {
    renderPanel("periodChange", 0, snapshots.slice(0, 1));
    expect(
      screen.getByText(/스냅샷이 2개 미만이거나 시작\/종료 평가금액이 유효하지 않아/),
    ).toBeInTheDocument();
  });

  it("renders degraded period comparison text when snapshot values are invalid", () => {
    renderPanel("periodChange", 0, [
      { ...snapshots[0]!, total_value_krw: "0" },
      snapshots[1]!,
    ]);

    expect(
      screen.getByText(/스냅샷이 2개 미만이거나 시작\/종료 평가금액이 유효하지 않아/),
    ).toBeInTheDocument();
    expect(screen.queryByText("+0.00%")).not.toBeInTheDocument();
  });

  it("does not render zero summary period percent when snapshot evidence is unusable", () => {
    renderPanel(
      "periodChange",
      0,
      [snapshots[0]!, { ...snapshots[1]!, total_value_krw: "0" }],
      { ...summary, period_change_pct: "0.00" },
    );

    expect(screen.queryByText("+0.00%")).not.toBeInTheDocument();
    expect(screen.getByText("근거 부족")).toBeInTheDocument();
    expect(screen.getByText("검증 지표 근거 부족")).toBeInTheDocument();
    expect(screen.queryByText("요약 API 기간 변화율")).not.toBeInTheDocument();
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
    expect(screen.getByText(hhiFormulaLabel)).toBeInTheDocument();
    expect(screen.queryByText(/매수/)).not.toBeInTheDocument();
    expect(screen.queryByText(/매도/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "리밸런싱 검토" })).toHaveAttribute(
      "href",
      "/clients/client-001#rebalance",
    );
  });

  it("degrades concentration evidence when asset-class evidence is unusable", () => {
    renderPanel("concentration", 0, snapshots, {
      ...summary,
      total_value_krw: "0",
      asset_class_breakdown: {},
    });

    expect(screen.queryByText(hhiFormulaLabel)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/portfolio\.summary\.asset_class_breakdown/),
    ).not.toBeInTheDocument();
    expect(screen.getByText("집중도 근거 저하")).toBeInTheDocument();
  });

  it("renders source details as a semantic disclosure", () => {
    renderPanel("totalAssets");

    const summaryElement = screen.getByText("출처 상세");
    const sourceToken = screen.getByText("portfolio.summary.total_value_krw");
    const details = sourceToken.closest("details");

    expect(summaryElement.closest("summary")).not.toBeNull();
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
    expect(sourceToken).not.toBeVisible();
    expect(sourceToken).toHaveClass("break-words");
    expect(sourceToken).toHaveClass("[overflow-wrap:anywhere]");
    expect(sourceToken).not.toHaveClass("break-keep");
  });
});
