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
import { useLocale } from "@/lib/i18n/locale-provider";

interface DimensionBarsProps {
  data: Array<{ label: string; weight_pct: string; pnl_pct: string }>;
}

const ASSET_CLASS_LABEL_KEYS: Record<string, string> = {
  stock_kr: "dashboard.alloc.stockKr",
  stock_us: "dashboard.alloc.stockUs",
  crypto: "dashboard.alloc.crypto",
  cash: "dashboard.alloc.cash",
  fx: "dashboard.alloc.fx",
  other: "dashboard.alloc.other",
};

export function DimensionBars({ data }: DimensionBarsProps) {
  const { t } = useLocale();
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        {t("common.empty")}
      </div>
    );
  }

  const weightKey = t("dashboard.dimension.weight");
  const returnKey = t("dashboard.dimension.return");

  const chartData = data.map((d) => ({
    name: ASSET_CLASS_LABEL_KEYS[d.label] ? t(ASSET_CLASS_LABEL_KEYS[d.label]!) : d.label,
    [weightKey]: Number(d.weight_pct),
    [returnKey]: Number(d.pnl_pct),
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
            dataKey={weightKey}
            fill="#6366f1"
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          />
          <Bar
            dataKey={returnKey}
            fill="#10b981"
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
