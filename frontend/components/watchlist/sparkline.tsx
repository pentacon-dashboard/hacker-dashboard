"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { getOhlc } from "@/lib/api/symbols";

interface SparklineProps {
  market: string;
  code: string;
}

export function Sparkline({ market, code }: SparklineProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["ohlc-sparkline", market, code],
    queryFn: () => getOhlc(market, code, "1d", 24),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="h-8 w-24 animate-pulse rounded bg-muted" aria-hidden="true" />
    );
  }

  if (!data || data.length === 0) {
    return <div className="h-8 w-24 text-xs text-muted-foreground">-</div>;
  }

  const first = data[0]?.close ?? 0;
  const last = data[data.length - 1]?.close ?? 0;
  const color = last >= first ? "#22c55e" : "#ef4444";

  const chartData = data.map((bar) => ({ v: bar.close }));

  return (
    <div className="h-8 w-24" aria-label="24일 종가 스파크라인">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
