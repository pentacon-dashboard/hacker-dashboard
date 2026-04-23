"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

interface DimensionBarsProps {
  data: Array<{ label: string; weight_pct: string; pnl_pct: string }>;
}

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "국내 주식",
  stock_us: "해외 주식",
  crypto: "암호화폐",
  cash: "현금",
  fx: "외환",
  other: "기타",
};

export function DimensionBars({ data }: DimensionBarsProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        디멘션 데이터 없음
      </div>
    );
  }

  const chartData = data.map((d) => ({
    name: ASSET_CLASS_LABELS[d.label] ?? d.label,
    비중: Number(d.weight_pct),
    수익률: Number(d.pnl_pct),
  }));

  return (
    <div className="h-56 w-full" data-testid="dimension-bars">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
          barCategoryGap={12}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11 }}
            width={72}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              `${value > 0 ? "+" : ""}${value.toFixed(2)}%`,
              name,
            ]}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            iconSize={10}
            height={20}
          />
          <Bar
            dataKey="비중"
            fill="#6366f1"
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          />
          <Bar
            dataKey="수익률"
            fill="#10b981"
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
