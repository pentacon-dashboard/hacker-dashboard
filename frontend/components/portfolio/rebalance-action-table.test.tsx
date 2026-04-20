import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RebalanceActionTable } from "./rebalance-action-table";
import type { RebalanceAction } from "@/lib/api/rebalance";

const SELL_ACTION: RebalanceAction = {
  action: "sell",
  market: "upbit",
  code: "KRW-BTC",
  asset_class: "crypto",
  quantity: "0.02",
  estimated_value_krw: "1700000",
  reason: "crypto 비중 74% → 목표 30%",
};

const BUY_ACTION: RebalanceAction = {
  action: "buy",
  market: "yahoo",
  code: "AAPL",
  asset_class: "stock_us",
  quantity: "3",
  estimated_value_krw: "850000",
  reason: "stock_us 목표까지 +21% 부족",
};

const NULL_VALUE_ACTION: RebalanceAction = {
  action: "buy",
  market: "yahoo",
  code: "TSLA",
  asset_class: "stock_us",
  quantity: "1",
  estimated_value_krw: null,
  reason: "현재가 조회 실패",
};

describe("RebalanceActionTable", () => {
  it("actions=[] 일 때 '리밸런싱 필요 없음' 메시지 카드가 표시됨", () => {
    render(<RebalanceActionTable actions={[]} />);
    expect(screen.getByText("리밸런싱 필요 없음")).toBeInTheDocument();
  });

  it("Buy 액션에 매수 배지가 표시됨", () => {
    render(<RebalanceActionTable actions={[BUY_ACTION]} />);
    const badge = screen.getByTestId("action-badge-buy");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("매수");
  });

  it("Sell 액션에 매도 배지가 표시됨", () => {
    render(<RebalanceActionTable actions={[SELL_ACTION]} />);
    const badge = screen.getByTestId("action-badge-sell");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("매도");
  });

  it("Buy 배지에 초록색 클래스가 포함됨", () => {
    render(<RebalanceActionTable actions={[BUY_ACTION]} />);
    const badge = screen.getByTestId("action-badge-buy");
    expect(badge.className).toContain("green");
  });

  it("Sell 배지에 빨간색 클래스가 포함됨", () => {
    render(<RebalanceActionTable actions={[SELL_ACTION]} />);
    const badge = screen.getByTestId("action-badge-sell");
    expect(badge.className).toContain("red");
  });

  it("estimated_value_krw=null 일 때 '조회 실패' 배지가 표시됨", () => {
    render(<RebalanceActionTable actions={[NULL_VALUE_ACTION]} />);
    const badge = screen.getByTestId("value-failed-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("조회 실패");
  });

  it("여러 액션 표시 시 sell이 buy보다 먼저 표시됨", () => {
    render(<RebalanceActionTable actions={[BUY_ACTION, SELL_ACTION]} />);
    const rows = screen.getAllByRole("row");
    // 첫 row는 헤더, 두 번째가 데이터 첫 행
    // sell이 먼저여야 하므로 두 번째 row에 매도 배지가 있어야 함
    const sellBadge = screen.getByTestId("action-badge-sell");
    const buyBadge = screen.getByTestId("action-badge-buy");
    const allRows = rows.slice(1); // 헤더 제외
    const sellRowIdx = allRows.findIndex((r) => r.contains(sellBadge));
    const buyRowIdx = allRows.findIndex((r) => r.contains(buyBadge));
    expect(sellRowIdx).toBeLessThan(buyRowIdx);
  });

  it("종목 코드가 'market / code' 형식으로 표시됨", () => {
    render(<RebalanceActionTable actions={[SELL_ACTION]} />);
    expect(screen.getByText("upbit / KRW-BTC")).toBeInTheDocument();
  });

  it("자산군이 한글 라벨로 표시됨", () => {
    render(<RebalanceActionTable actions={[SELL_ACTION]} />);
    expect(screen.getByText("암호화폐")).toBeInTheDocument();
  });
});
