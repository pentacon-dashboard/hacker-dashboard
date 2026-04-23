"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

// BE /market/indices 실제 스키마
export interface IndexSnapshot {
  ticker: string;
  display_name: string;
  value: string;
  change_pct: string;
  change_abs: string;
  sparkline_7d: number[];
}

interface IndexKpiStripProps {
  indices: IndexSnapshot[];
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

function formatValue(ticker: string, value: string): string {
  const num = parseFloat(value.replace(/,/g, ""));
  if (isNaN(num)) return value;
  if (ticker === "USDKRW" || num >= 1000) {
    return num.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
  }
  return num.toFixed(2);
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
        const positive = !idx.change_pct.startsWith("-");
        return (
          <div
            key={idx.ticker}
            role="listitem"
            className="flex min-w-[140px] shrink-0 items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2"
            data-testid={`kpi-${idx.ticker}`}
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-muted-foreground">{idx.display_name}</p>
              <p className="mt-0.5 text-sm font-bold tabular-nums">
                {formatValue(idx.ticker, idx.value)}
              </p>
              <div className={cn("flex items-center gap-0.5 text-xs font-semibold", positive ? "text-green-500" : "text-destructive")}>
                {positive ? (
                  <TrendingUp className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3" aria-hidden="true" />
                )}
                {idx.change_pct}%
              </div>
            </div>
            <Sparkline data={idx.sparkline_7d} positive={positive} />
          </div>
        );
      })}
    </div>
  );
}
