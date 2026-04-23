import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  IndicatorSubcharts,
  type RsiPoint,
  type MacdPoint,
} from "./indicator-subcharts";

// Recharts 내부에서 SVG 측정이 jsdom 에서 동작하지 않으므로
// ResponsiveContainer 를 mock 처리
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 300, height: 120 }}>{children}</div>
    ),
  };
});

const MOCK_RSI: RsiPoint[] = Array.from({ length: 5 }, (_, i) => ({
  t: `2026-04-${String(i + 1).padStart(2, "0")}T00:00:00`,
  v: 40 + i * 5,
}));

const MOCK_MACD: MacdPoint[] = Array.from({ length: 5 }, (_, i) => ({
  t: `2026-04-${String(i + 1).padStart(2, "0")}T00:00:00`,
  macd: 1.0 + i * 0.5,
  signal: 0.8 + i * 0.4,
  histogram: 0.2 + i * 0.1,
}));

describe("IndicatorSubcharts", () => {
  it("RSI 서브차트를 렌더한다", () => {
    render(<IndicatorSubcharts rsi={MOCK_RSI} macd={MOCK_MACD} />);
    expect(screen.getByTestId("indicator-subchart-rsi")).toBeInTheDocument();
  });

  it("MACD 서브차트를 렌더한다", () => {
    render(<IndicatorSubcharts rsi={MOCK_RSI} macd={MOCK_MACD} />);
    expect(screen.getByTestId("indicator-subchart-macd")).toBeInTheDocument();
  });

  it("빈 배열 시 '지표 데이터 없음' empty state를 표시한다", () => {
    render(<IndicatorSubcharts rsi={[]} macd={[]} />);
    expect(screen.getByTestId("indicator-subcharts-empty")).toBeInTheDocument();
    expect(screen.getByText("지표 데이터 없음")).toBeInTheDocument();
  });

  it("latest 값 헤더에 RSI: / MACD: 문자열이 표시된다", () => {
    render(<IndicatorSubcharts rsi={MOCK_RSI} macd={MOCK_MACD} />);
    // RSI 헤더
    const rsiHeader = screen.getByTestId("indicator-subchart-rsi");
    expect(rsiHeader.textContent).toMatch(/RSI:/);
    // MACD 헤더
    const macdHeader = screen.getByTestId("indicator-subchart-macd");
    expect(macdHeader.textContent).toMatch(/MACD:/);
  });
});
