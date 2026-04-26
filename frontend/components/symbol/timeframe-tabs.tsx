"use client";

import { useLocale } from "@/lib/i18n/locale-provider";

export type Timeframe = "1m" | "5m" | "15m" | "60m" | "day" | "week" | "month";

const TABS: Array<{ value: Timeframe; labelKey: string }> = [
  { value: "1m", labelKey: "symbol.tf.1m" },
  { value: "5m", labelKey: "symbol.tf.5m" },
  { value: "15m", labelKey: "symbol.tf.15m" },
  { value: "60m", labelKey: "symbol.tf.60m" },
  { value: "day", labelKey: "symbol.tf.day" },
  { value: "week", labelKey: "symbol.tf.week" },
  { value: "month", labelKey: "symbol.tf.month" },
];

interface TimeframeTabsProps {
  value: Timeframe;
  onChange: (v: Timeframe) => void;
}

export function TimeframeTabs({ value, onChange }: TimeframeTabsProps) {
  const { t } = useLocale();
  return (
    <div
      role="tablist"
      aria-label={t("symbol.chartTimeframe")}
      className="flex items-center gap-1 rounded-lg border bg-muted/50 p-1"
      data-testid="timeframe-tabs"
    >
      {TABS.map((tab) => (
        <button
          key={tab.value}
          role="tab"
          aria-selected={value === tab.value}
          data-testid={`timeframe-tab-${tab.value}`}
          onClick={() => onChange(tab.value)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
            value === tab.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t(tab.labelKey)}
        </button>
      ))}
    </div>
  );
}
