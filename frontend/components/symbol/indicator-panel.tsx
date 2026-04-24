"use client";

import { useLocale } from "@/lib/i18n/locale-provider";

export interface IndicatorBundle {
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  bollinger_upper: number | null;
  bollinger_lower: number | null;
  stochastic: number | null;
  signal: "buy" | "hold" | "sell";
}

interface IndicatorPanelProps {
  bundle: IndicatorBundle | null;
  isLoading?: boolean;
}

function IndicatorRow({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number | string | null;
  suffix?: string;
}) {
  const numeric = typeof value === "string" ? Number(value) : value;
  const display =
    numeric != null && Number.isFinite(numeric)
      ? `${numeric.toFixed(2)}${suffix ?? ""}`
      : "-";
  return (
    <div className="flex items-center justify-between gap-2 py-1 border-b last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-semibold tabular-nums">{display}</span>
    </div>
  );
}

export function IndicatorPanel({ bundle, isLoading = false }: IndicatorPanelProps) {
  const { t } = useLocale();

  if (isLoading) {
    return (
      <div className="space-y-2" data-testid="indicator-panel-loading">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (!bundle) {
    return (
      <div
        className="flex h-24 items-center justify-center text-sm text-muted-foreground"
        data-testid="indicator-panel-empty"
      >
        {t("symbol.noIndicator")}
      </div>
    );
  }

  return (
    <div className="space-y-0" data-testid="indicator-panel">
      <IndicatorRow label="RSI (14)" value={bundle.rsi_14} />
      <IndicatorRow label="MACD" value={bundle.macd} />
      <IndicatorRow label="MACD Signal" value={bundle.macd_signal} />
      <IndicatorRow label={t("symbol.indicator.bollingerUpper")} value={bundle.bollinger_upper} />
      <IndicatorRow label={t("symbol.indicator.bollingerLower")} value={bundle.bollinger_lower} />
      <IndicatorRow label={t("symbol.indicator.stochastic")} value={bundle.stochastic} suffix="%" />
    </div>
  );
}
