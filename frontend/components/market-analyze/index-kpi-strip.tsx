"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface IndexKpi {
  code: string;
  name: string;
  value: number;
  change_pct: number;
  sparkline: number[];
}

interface IndexKpiStripProps {
  indices: IndexKpi[];
  loading?: boolean;
}

function Sparkline({ data, positive }: { data: number[]; positive: boolean }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 56;
  const h = 24;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      aria-hidden="true"
      className="shrink-0"
    >
      <polyline
        points={pts}
        fill="none"
        stroke={positive ? "rgb(34 197 94)" : "rgb(239 68 68)"}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function formatValue(code: string, value: number): string {
  if (code === "USDKRW") {
    return value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
  }
  if (value >= 1000) {
    return value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

export function IndexKpiStrip({ indices, loading }: IndexKpiStripProps) {
  if (loading) {
    return (
      <div className="flex gap-2 overflow-x-auto pb-1">
        {[...Array(7)].map((_, i) => (
          <div
            key={i}
            className="h-16 min-w-[130px] shrink-0 animate-pulse rounded-lg border border-border bg-muted/20"
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className="flex gap-2 overflow-x-auto pb-1"
      role="list"
      aria-label="글로벌 지수 KPI"
      data-testid="index-kpi-strip"
    >
      {indices.map((idx) => {
        const positive = idx.change_pct >= 0;
        return (
          <div
            key={idx.code}
            role="listitem"
            className="flex min-w-[140px] shrink-0 items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2"
            data-testid={`kpi-${idx.code}`}
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-muted-foreground">{idx.name}</p>
              <p className="mt-0.5 text-sm font-bold tabular-nums">
                {formatValue(idx.code, idx.value)}
              </p>
              <div className={cn("flex items-center gap-0.5 text-xs font-semibold", positive ? "text-green-500" : "text-destructive")}>
                {positive ? (
                  <TrendingUp className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3" aria-hidden="true" />
                )}
                {positive ? "+" : ""}
                {idx.change_pct.toFixed(2)}%
              </div>
            </div>
            <Sparkline data={idx.sparkline} positive={positive} />
          </div>
        );
      })}
    </div>
  );
}
