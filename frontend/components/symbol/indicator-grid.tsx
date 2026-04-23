"use client";

import { signedColorClass } from "@/lib/utils/format";

export interface IndicatorMetrics {
  change_pct: string;
  avg_cost: string | null;
  ma20: string | null;
  ma60: string | null;
  volume: string;
  signal: "buy" | "hold" | "sell";
}

interface IndicatorGridProps {
  metrics: IndicatorMetrics | null;
  isLoading?: boolean;
}

const SIGNAL_LABELS: Record<string, { label: string; cls: string }> = {
  buy: { label: "매수", cls: "text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30" },
  hold: { label: "보유", cls: "text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30" },
  sell: { label: "매도", cls: "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30" },
};

interface MetricCardProps {
  label: string;
  value: string;
  colorClass?: string;
}

function MetricCard({ label, value, colorClass }: MetricCardProps) {
  return (
    <div className="rounded-xl border bg-card p-3 shadow-sm">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className={`mt-1 text-sm font-bold tabular-nums ${colorClass ?? "text-foreground"}`}>
        {value}
      </p>
    </div>
  );
}

export function IndicatorGrid({ metrics, isLoading = false }: IndicatorGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6" data-testid="indicator-grid-loading">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div
        className="flex h-16 items-center justify-center text-sm text-muted-foreground"
        data-testid="indicator-grid-empty"
      >
        지표 데이터 없음
      </div>
    );
  }

  const changePct = Number(metrics.change_pct);
  const signalInfo = SIGNAL_LABELS[metrics.signal] ?? SIGNAL_LABELS["hold"]!;

  return (
    <div
      className="grid grid-cols-3 gap-2 sm:grid-cols-6"
      data-testid="indicator-grid"
    >
      <MetricCard
        label="등락률"
        value={`${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}%`}
        colorClass={signedColorClass(changePct)}
      />
      <MetricCard
        label="평단가"
        value={metrics.avg_cost ?? "-"}
      />
      <MetricCard label="MA20" value={metrics.ma20 ?? "-"} />
      <MetricCard label="MA60" value={metrics.ma60 ?? "-"} />
      <MetricCard label="거래량" value={metrics.volume} />
      <div className="rounded-xl border bg-card p-3 shadow-sm" data-testid="signal-card">
        <p className="text-[10px] text-muted-foreground">시그널</p>
        <span
          className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-bold ${signalInfo.cls}`}
        >
          {signalInfo.label}
        </span>
      </div>
    </div>
  );
}
