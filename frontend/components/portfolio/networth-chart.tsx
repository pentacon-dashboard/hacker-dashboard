"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { SnapshotResponse } from "@/lib/api/portfolio";
import { formatKRW } from "@/lib/utils/format";

interface NetworthChartProps {
  snapshots: SnapshotResponse[];
}

export function NetworthChart({ snapshots }: NetworthChartProps) {
  if (snapshots.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        스냅샷 데이터 없음
      </div>
    );
  }

  const data = snapshots.map((s) => ({
    date: s.snapshot_date,
    value: Number(s.total_value_krw),
  }));

  return (
    <div data-testid="networth-chart" className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <defs>
            <linearGradient id="networthGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(5)} // MM-DD
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) =>
              v >= 1_000_000
                ? `${(v / 1_000_000).toFixed(0)}M`
                : v >= 1_000
                  ? `${(v / 1_000).toFixed(0)}K`
                  : String(v)
            }
            width={52}
          />
          <Tooltip
            formatter={(value: number) => [formatKRW(value), "순자산"]}
            labelFormatter={(label: string) => label}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#networthGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
