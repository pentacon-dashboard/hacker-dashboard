"use client";

import { useEffect, useRef } from "react";
import type { OhlcBar } from "@/lib/api/symbols";

interface CandlestickChartProps {
  data: OhlcBar[];
  market: string;
  code: string;
}

type ChartInstance = {
  remove: () => void;
  timeScale: () => { fitContent: () => void };
};

type SeriesApi = {
  setData: (d: unknown[]) => void;
  applyOptions: (opts: unknown) => void;
};

type ChartModule = {
  createChart: (
    el: HTMLElement,
    opts: unknown,
  ) => ChartInstance & {
    addCandlestickSeries: (opts?: unknown) => SeriesApi;
    addHistogramSeries: (opts?: unknown) => SeriesApi;
    addLineSeries: (opts?: unknown) => SeriesApi;
    applyOptions: (opts: unknown) => void;
    resize: (w: number, h: number) => void;
  };
  CrosshairMode: { Normal: number };
};

function computeMA(data: OhlcBar[], period: number): { time: string; value: number }[] {
  const result: { time: string; value: number }[] = [];
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j]?.close ?? 0;
    }
    const bar = data[i];
    if (bar) {
      result.push({ time: bar.ts.split("T")[0] ?? bar.ts, value: sum / period });
    }
  }
  return result;
}

export function CandlestickChart({ data, market: _market, code: _code }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<ChartModule["createChart"]> | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    let cancelled = false;
    let ro: ResizeObserver | null = null;

    void (async () => {
      const mod = (await import("lightweight-charts")) as unknown as ChartModule;
      if (cancelled) return;
      const el = containerRef.current;
      if (!el) return;

      const isDark = document.documentElement.classList.contains("dark");
      const bg = isDark ? "#0f172a" : "#ffffff";
      const textColor = isDark ? "#94a3b8" : "#64748b";
      const gridColor = isDark ? "#1e293b" : "#f1f5f9";

      const chart = mod.createChart(el, {
        width: el.clientWidth,
        height: 400,
        layout: {
          background: { color: bg },
          textColor,
        },
        grid: {
          vertLines: { color: gridColor },
          horzLines: { color: gridColor },
        },
        crosshair: { mode: mod.CrosshairMode.Normal },
        rightPriceScale: { borderColor: gridColor },
        timeScale: { borderColor: gridColor, timeVisible: true },
      });

      chartRef.current = chart;

      // 캔들 시리즈
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      const candleData = data.map((bar) => ({
        time: bar.ts.split("T")[0] ?? bar.ts,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }));
      candleSeries.setData(candleData);

      // 거래량 서브차트 (히스토그램)
      const volumeSeries = chart.addHistogramSeries({
        color: "#94a3b8",
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volumeSeries.applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      const volumeData = data
        .filter((bar) => bar.volume != null)
        .map((bar) => ({
          time: bar.ts.split("T")[0] ?? bar.ts,
          value: bar.volume ?? 0,
          color: bar.close >= bar.open ? "#22c55e40" : "#ef444440",
        }));
      volumeSeries.setData(volumeData);

      // MA20
      const ma20 = chart.addLineSeries({
        color: "#3b82f6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ma20.setData(computeMA(data, 20));

      // MA60
      const ma60 = chart.addLineSeries({
        color: "#f59e0b",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ma60.setData(computeMA(data, 60));

      chart.timeScale().fitContent();

      if (cancelled) {
        try { chart.remove(); } catch { /* disposed */ }
        return;
      }

      ro = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (!cancelled) {
            try { chart.resize(width, height); } catch { /* disposed */ }
          }
        }
      });
      ro.observe(el);
    })();

    return () => {
      cancelled = true;
      ro?.disconnect();
      if (chartRef.current) {
        try { chartRef.current.remove(); } catch { /* already disposed */ }
        chartRef.current = null;
      }
    };
  }, [data]);

  return (
    <div
      ref={containerRef}
      data-testid="chart-container"
      className="w-full rounded-lg border bg-background"
      style={{ minHeight: 400 }}
      aria-label="캔들스틱 차트"
    />
  );
}
