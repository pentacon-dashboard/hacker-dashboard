"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { formatPct } from "@/lib/utils/format";

interface AssetPieChartProps {
  breakdown: Record<string, string>;
}

const ASSET_COLORS: Record<string, string> = {
  stock_kr: "#3b82f6",
  stock_us: "#8b5cf6",
  crypto: "#f97316",
  fx: "#22c55e",
  cash: "#6b7280",
};

const ASSET_LABELS: Record<string, string> = {
  stock_kr: "국내주식",
  stock_us: "해외주식",
  crypto: "코인",
  fx: "환율",
  cash: "현금",
};

export function AssetPieChart({ breakdown }: AssetPieChartProps) {
  const data = Object.entries(breakdown)
    .map(([key, value]) => ({
      name: ASSET_LABELS[key] ?? key,
      key,
      value: Math.round(Number(value) * 10000) / 100, // 0.5 → 50.00 (%)
    }))
    .filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        자산 데이터 없음
      </div>
    );
  }

  return (
    <div data-testid="asset-pie" className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="80%"
            dataKey="value"
            nameKey="name"
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell
                key={entry.key}
                fill={ASSET_COLORS[entry.key] ?? "#94a3b8"}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [
              formatPct(value / 100, { signed: false }),
              "",
            ]}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value: string) => (
              <span className="text-xs">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
