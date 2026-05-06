"use client";

import { cn } from "@/lib/utils";
import { signedColorClass } from "@/lib/utils/format";

export type KpiAccent =
  | "blue"
  | "green"
  | "amber"
  | "rose"
  | "violet"
  | "slate";

interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaValue?: number;
  icon?: React.ReactNode;
  accent?: KpiAccent;
  tone?: "neutral" | "positive" | "negative";
  testId?: string;
  onClick?: () => void;
  selected?: boolean;
  controlsId?: string;
}

const accentBg: Record<KpiAccent, string> = {
  blue: "bg-blue-100 text-blue-600 dark:bg-blue-500/15 dark:text-blue-300",
  green:
    "bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300",
  amber:
    "bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300",
  rose: "bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300",
  violet:
    "bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary",
  slate:
    "bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300",
};

export function KpiCard({
  label,
  value,
  delta,
  deltaValue,
  icon,
  accent = "slate",
  tone = "neutral",
  testId,
  onClick,
  selected,
  controlsId,
}: KpiCardProps) {
  const deltaColor =
    deltaValue != null
      ? signedColorClass(deltaValue)
      : tone === "positive"
        ? "text-green-600 dark:text-green-400"
        : tone === "negative"
          ? "text-red-600 dark:text-red-400"
          : "text-muted-foreground";

  const cardClassName = cn(
    "rounded-xl border bg-card p-4 shadow-sm transition-colors",
    "flex min-h-[118px] min-w-0 flex-col gap-2 text-left",
    onClick &&
      "w-full cursor-pointer hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    selected && "bg-primary/5 ring-2 ring-primary/35",
  );

  const content = (
    <>
      <div className="flex min-w-0 items-start justify-between gap-2">
        <span className="min-w-0 overflow-hidden text-ellipsis break-keep text-xs font-medium leading-tight text-muted-foreground">
          {label}
        </span>
        {icon && (
          <span
            aria-hidden="true"
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
              accentBg[accent],
            )}
          >
            {icon}
          </span>
        )}
      </div>
      <div className="flex min-w-0 flex-col items-start gap-1">
        <span
          className="min-w-0 max-w-full overflow-hidden text-ellipsis break-keep text-base font-semibold leading-tight text-foreground sm:text-lg md:text-xl"
          title={value}
        >
          {value}
        </span>
        {delta && (
          <span className={cn("max-w-full shrink-0 overflow-hidden text-ellipsis break-keep text-xs font-semibold leading-tight", deltaColor)}>
            {delta}
          </span>
        )}
      </div>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        data-testid={testId}
        className={cardClassName}
        onClick={onClick}
        aria-expanded={selected}
        aria-controls={controlsId}
      >
        {content}
      </button>
    );
  }

  return (
    <div data-testid={testId} className={cardClassName}>
      {content}
    </div>
  );
}
