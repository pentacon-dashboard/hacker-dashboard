import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SectorHeatmap, type SectorHeatmapTile } from "./sector-heatmap";

const MOCK_TILES: SectorHeatmapTile[] = [
  { sector: "Tech", weight_pct: "32.4", pnl_pct: "5.12", intensity: "0.51" },
  { sector: "Finance", weight_pct: "14.2", pnl_pct: "2.30", intensity: "0.23" },
  { sector: "Energy", weight_pct: "8.5", pnl_pct: "-1.20", intensity: "-0.12" },
];

describe("SectorHeatmap", () => {
  it("타일 3개를 렌더한다", () => {
    render(<SectorHeatmap tiles={MOCK_TILES} />);
    expect(screen.getByTestId("sector-heatmap")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-tile-Tech")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-tile-Finance")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-tile-Energy")).toBeInTheDocument();
  });

  it("빈 배열이면 empty state를 렌더한다", () => {
    render(<SectorHeatmap tiles={[]} />);
    expect(screen.getByTestId("sector-heatmap-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("sector-heatmap")).not.toBeInTheDocument();
  });

  it("양수 pnl_pct는 + 기호와 함께 표시된다", () => {
    render(<SectorHeatmap tiles={[MOCK_TILES[0]!]} />);
    expect(screen.getByText("+5.12%")).toBeInTheDocument();
  });

  it("음수 pnl_pct는 - 기호와 함께 표시된다", () => {
    render(<SectorHeatmap tiles={[MOCK_TILES[2]!]} />);
    expect(screen.getByText("-1.20%")).toBeInTheDocument();
  });

  it("버튼에 aria-label이 설정된다", () => {
    render(<SectorHeatmap tiles={[MOCK_TILES[0]!]} />);
    const btn = screen.getByRole("button", { name: /Tech 섹터 수익률/ });
    expect(btn).toBeInTheDocument();
  });
});
