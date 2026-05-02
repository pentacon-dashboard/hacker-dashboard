import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OhlcBar } from "@/lib/api/symbols";
import { CandlestickChart } from "./candlestick-chart";

const chartMocks = vi.hoisted(() => ({
  candleSetData: vi.fn(),
  volumeSetData: vi.fn(),
  lineSetData: vi.fn(),
  remove: vi.fn(),
  resize: vi.fn(),
  fitContent: vi.fn(),
}));

vi.mock("lightweight-charts", () => ({
  CrosshairMode: { Normal: 0 },
  createChart: vi.fn(() => ({
    addCandlestickSeries: () => ({
      setData: chartMocks.candleSetData,
      applyOptions: vi.fn(),
    }),
    addHistogramSeries: () => ({
      setData: chartMocks.volumeSetData,
      applyOptions: vi.fn(),
    }),
    addLineSeries: () => ({
      setData: chartMocks.lineSetData,
      applyOptions: vi.fn(),
    }),
    applyOptions: vi.fn(),
    remove: chartMocks.remove,
    resize: chartMocks.resize,
    timeScale: () => ({ fitContent: chartMocks.fitContent }),
  })),
}));

class MockResizeObserver implements ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

const VALID_BAR: OhlcBar = {
  ts: "2026-04-29T00:00:00+09:00",
  open: 219500,
  high: 228000,
  low: 218500,
  close: 226000,
  volume: 20363756,
};

describe("CandlestickChart", () => {
  beforeEach(() => {
    chartMocks.candleSetData.mockReset();
    chartMocks.volumeSetData.mockReset();
    chartMocks.lineSetData.mockReset();
    chartMocks.remove.mockReset();
    chartMocks.resize.mockReset();
    chartMocks.fitContent.mockReset();
    vi.stubGlobal("ResizeObserver", MockResizeObserver);
  });

  it("filters OHLC rows with null price fields before passing data to lightweight-charts", async () => {
    const invalidLatest = {
      ts: "2026-04-30T00:00:00+09:00",
      open: null,
      high: null,
      low: null,
      close: null,
      volume: 25294554,
    } as unknown as OhlcBar;

    render(
      <CandlestickChart
        data={[VALID_BAR, invalidLatest]}
        market="naver_kr"
        code="005930"
      />,
    );

    await waitFor(() => expect(chartMocks.candleSetData).toHaveBeenCalled());

    expect(chartMocks.candleSetData).toHaveBeenCalledWith([
      {
        time: "2026-04-29",
        open: 219500,
        high: 228000,
        low: 218500,
        close: 226000,
      },
    ]);
  });
});
