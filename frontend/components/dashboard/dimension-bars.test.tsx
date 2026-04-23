import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DimensionBars } from "./dimension-bars";

describe("DimensionBars", () => {
  it("빈 데이터면 empty 메시지를 표시한다", () => {
    render(<DimensionBars data={[]} />);
    expect(screen.getByText("디멘션 데이터 없음")).toBeInTheDocument();
  });

  it("데이터가 있으면 차트 컨테이너를 렌더한다", () => {
    render(
      <DimensionBars
        data={[
          { label: "stock_us", weight_pct: "43.20", pnl_pct: "15.80" },
          { label: "stock_kr", weight_pct: "21.80", pnl_pct: "4.51" },
        ]}
      />,
    );
    expect(screen.getByTestId("dimension-bars")).toBeInTheDocument();
  });

  it("empty 상태가 아닐 때 dimension-bars testid 가 존재한다", () => {
    const { container } = render(
      <DimensionBars
        data={[{ label: "crypto", weight_pct: "18.80", pnl_pct: "5.12" }]}
      />,
    );
    expect(container.querySelector('[data-testid="dimension-bars"]')).toBeInTheDocument();
  });
});
