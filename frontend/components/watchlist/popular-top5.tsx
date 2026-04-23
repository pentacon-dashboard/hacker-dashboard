"use client";

import { TrendingUp, TrendingDown } from "lucide-react";

export interface TopListItem {
  rank: number;
  ticker: string;
  name: string;
  change_pct: string;
}

interface PopularTop5Props {
  items: TopListItem[];
  title?: string;
}

export function PopularTop5({ items, title = "인기 TOP 5" }: PopularTop5Props) {
  if (items.length === 0) {
    return (
      <div
        className="flex h-24 items-center justify-center text-sm text-muted-foreground"
        data-testid="popular-top5-empty"
      >
        데이터 없음
      </div>
    );
  }

  return (
    <div data-testid="popular-top5">
      <h3 className="mb-2 text-xs font-semibold text-muted-foreground">{title}</h3>
      <ul className="space-y-1.5">
        {items.slice(0, 5).map((item) => {
          const change = Number(item.change_pct);
          const isPos = change >= 0;
          return (
            <li
              key={item.ticker}
              className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/50"
              data-testid={`popular-item-${item.ticker}`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums w-4">
                  {item.rank}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium">{item.ticker}</p>
                  <p className="truncate text-[10px] text-muted-foreground">{item.name}</p>
                </div>
              </div>
              <span
                className={`flex shrink-0 items-center gap-0.5 text-xs font-semibold tabular-nums ${
                  isPos
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {isPos ? (
                  <TrendingUp className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3" aria-hidden="true" />
                )}
                {isPos ? "+" : ""}
                {change.toFixed(2)}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
