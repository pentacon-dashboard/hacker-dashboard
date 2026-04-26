"use client";

import { cn } from "@/lib/utils";

export type PeriodKey = "1W" | "1M" | "3M" | "1Y";

export const PERIOD_DAYS: Record<PeriodKey, number> = {
  "1W": 7,
  "1M": 30,
  "3M": 90,
  "1Y": 365,
};

const ORDER: PeriodKey[] = ["1W", "1M", "3M", "1Y"];

interface PeriodTabsProps {
  value: PeriodKey;
  onChange: (next: PeriodKey) => void;
}

export function PeriodTabs({ value, onChange }: PeriodTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="기간 선택"
      className="inline-flex items-center rounded-md border bg-muted p-0.5 text-xs"
      data-testid="period-tabs"
    >
      {ORDER.map((key) => {
        const active = key === value;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(key)}
            data-testid={`period-tab-${key}`}
            className={cn(
              "rounded px-2.5 py-1 font-medium transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {key}
          </button>
        );
      })}
    </div>
  );
}
