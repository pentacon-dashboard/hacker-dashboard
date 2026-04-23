import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarketStatusCard } from "./market-status-card";

describe("MarketStatusCard", () => {
  it("펼침 상태에서 '시장 상태' 텍스트를 렌더한다", () => {
    render(<MarketStatusCard collapsed={false} />);
    expect(screen.getByText("시장 상태")).toBeInTheDocument();
  });

  it("펼침 상태에서 거래량 좋음 텍스트를 렌더한다", () => {
    render(<MarketStatusCard collapsed={false} />);
    expect(screen.getByText("거래량 좋음")).toBeInTheDocument();
  });

  it("접힘 상태에서 '시장 상태' 텍스트가 없고 aria-label이 있어야 한다", () => {
    render(<MarketStatusCard collapsed={true} />);
    expect(screen.queryByText("시장 상태")).not.toBeInTheDocument();
    // 접힘 상태에도 aria-label로 접근 가능
    const el = screen.getByLabelText(/시장 상태/);
    expect(el).toBeInTheDocument();
  });
});
