"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import type { TopListItem } from "./popular-top5";
import { useLocale } from "@/lib/i18n/locale-provider";
import { getSymbolDisplayParts } from "@/lib/market/display";

interface GainersLosersTop5Props {
  gainers: TopListItem[];
  losers: TopListItem[];
}

function MiniList({ items, variant }: { items: TopListItem[]; variant: "gainer" | "loser" }) {
  const { t } = useLocale();
  const isGainer = variant === "gainer";
  return (
    <div>
      <h4 className={`mb-1.5 flex items-center gap-1 text-[10px] font-semibold ${
        isGainer ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
      }`}>
        {isGainer ? (
          <TrendingUp className="h-3 w-3" aria-hidden="true" />
        ) : (
          <TrendingDown className="h-3 w-3" aria-hidden="true" />
        )}
        {isGainer ? t("watchlist.gainersTop") : t("watchlist.losersTop")}
      </h4>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t("common.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {items.slice(0, 5).map((item) => {
            const change = Number(item.change_pct);
            const displayParts = getSymbolDisplayParts(null, item.ticker, {
              fallbackName: item.name,
              includeMarket: false,
            });
            return (
              <li
                key={item.ticker}
                className="flex items-center justify-between gap-1"
                data-testid={`${variant}-item-${item.ticker}`}
              >
                <span
                  className="min-w-0 truncate text-xs"
                  title={displayParts.secondary ?? item.ticker}
                >
                  {displayParts.primary}
                </span>
                <span
                  className={`shrink-0 text-xs font-semibold tabular-nums ${
                    isGainer
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {change > 0 ? "+" : ""}
                  {change.toFixed(2)}%
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function GainersLosersTop5({ gainers, losers }: GainersLosersTop5Props) {
  return (
    <div className="grid grid-cols-2 gap-4" data-testid="gainers-losers-top5">
      <MiniList items={gainers} variant="gainer" />
      <MiniList items={losers} variant="loser" />
    </div>
  );
}
