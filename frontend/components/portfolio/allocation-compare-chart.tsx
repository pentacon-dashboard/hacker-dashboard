"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "한국 주식",
  stock_us: "미국 주식",
  crypto: "암호화폐",
  cash: "현금",
  fx: "외환",
};

interface AllocationCompareChartProps {
  currentAllocation: Record<string, number>;
  targetAllocation: Record<string, number>;
  expectedAllocation: Record<string, number>;
}

export function AllocationCompareChart({
  currentAllocation,
  targetAllocation,
  expectedAllocation,
}: AllocationCompareChartProps) {
  // 모든 자산군 키 수집
  const allKeys = Array.from(
    new Set([
      ...Object.keys(currentAllocation),
      ...Object.keys(targetAllocation),
      ...Object.keys(expectedAllocation),
    ]),
  );

  const chartData = allKeys.map((key) => ({
    name: ASSET_CLASS_LABELS[key] ?? key,
    현재: Math.round((currentAllocation[key] ?? 0) * 1000) / 10,
    목표: Math.round((targetAllocation[key] ?? 0) * 1000) / 10,
    예상: Math.round((expectedAllocation[key] ?? 0) * 1000) / 10,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12 }}
          className="fill-muted-foreground"
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 12 }}
          className="fill-muted-foreground"
          domain={[0, 100]}
        />
        <Tooltip
          formatter={(value: number) => [`${value}%`, undefined]}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="현재" fill="#3b82f6" radius={[3, 3, 0, 0]} />
        <Bar dataKey="목표" fill="#22c55e" radius={[3, 3, 0, 0]} />
        <Bar dataKey="예상" fill="#a855f7" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
