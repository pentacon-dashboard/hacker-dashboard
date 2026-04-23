"use client";

export type Timeframe = "1m" | "5m" | "15m" | "60m" | "day" | "week" | "month";

const TABS: Array<{ value: Timeframe; label: string }> = [
  { value: "1m", label: "1분" },
  { value: "5m", label: "5분" },
  { value: "15m", label: "15분" },
  { value: "60m", label: "60분" },
  { value: "day", label: "일" },
  { value: "week", label: "주" },
  { value: "month", label: "월" },
];

interface TimeframeTabsProps {
  value: Timeframe;
  onChange: (v: Timeframe) => void;
}

export function TimeframeTabs({ value, onChange }: TimeframeTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="차트 타임프레임"
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
          {tab.label}
        </button>
      ))}
    </div>
  );
}
