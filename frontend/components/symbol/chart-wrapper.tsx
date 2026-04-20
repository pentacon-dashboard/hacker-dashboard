"use client";

import dynamic from "next/dynamic";
import type { OhlcBar } from "@/lib/api/symbols";

const CandlestickChart = dynamic(
  () =>
    import("@/components/symbol/candlestick-chart").then(
      (m) => m.CandlestickChart,
    ),
  {
    ssr: false,
    loading: () => (
      <div
        className="w-full animate-pulse rounded-lg border bg-muted"
        style={{ minHeight: 400 }}
        aria-label="차트 로딩 중"
      />
    ),
  },
);

interface ChartWrapperProps {
  data: OhlcBar[];
  market: string;
  code: string;
}

export function ChartWrapper({ data, market, code }: ChartWrapperProps) {
  return <CandlestickChart data={data} market={market} code={code} />;
}
