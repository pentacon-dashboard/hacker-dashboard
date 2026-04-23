import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IndicatorGrid, type IndicatorMetrics } from "./indicator-grid";

const MOCK_METRICS: IndicatorMetrics = {
  change_pct: "2.45",
  avg_cost: "₩68,000",
  ma20: "₩72,500",
  ma60: "₩70,200",
  volume: "2.3M",
  signal: "buy",
};

describe("IndicatorGrid", () => {
  it("6개 카드를 렌더한다", () => {
    render(<IndicatorGrid metrics={MOCK_METRICS} />);
    expect(screen.getByTestId("indicator-grid")).toBeInTheDocument();
    expect(screen.getByTestId("signal-card")).toBeInTheDocument();
    // 6개 children: 등락률/평단/MA20/MA60/거래량/시그널
    const grid = screen.getByTestId("indicator-grid");
    expect(grid.children.length).toBe(6);
  });

  it("signal=buy이면 매수 배지를 표시한다", () => {
    render(<IndicatorGrid metrics={MOCK_METRICS} />);
    expect(screen.getByText("매수")).toBeInTheDocument();
  });

  it("signal=sell이면 매도 배지를 표시한다", () => {
    render(<IndicatorGrid metrics={{ ...MOCK_METRICS, signal: "sell" }} />);
    expect(screen.getByText("매도")).toBeInTheDocument();
  });

  it("metrics=null이면 empty state를 렌더한다", () => {
    render(<IndicatorGrid metrics={null} />);
    expect(screen.getByTestId("indicator-grid-empty")).toBeInTheDocument();
  });

  it("isLoading=true이면 loading skeleton을 렌더한다", () => {
    render(<IndicatorGrid metrics={null} isLoading />);
    expect(screen.getByTestId("indicator-grid-loading")).toBeInTheDocument();
  });
});
