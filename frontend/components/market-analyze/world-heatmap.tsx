"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Globe } from "lucide-react";
import { useLocale } from "@/lib/i18n/locale-provider";

// BE /market/world-heatmap 실제 스키마 (나라별)
export interface CountryHeatmapItem {
  country_code: string;
  country_name: string;
  change_pct: string;
  market_cap_usd: string;
}

interface WorldHeatmapProps {
  data: CountryHeatmapItem[];
  loading?: boolean;
}

function getHeatColor(pctStr: string): string {
  const pct = parseFloat(pctStr);
  if (isNaN(pct)) return "bg-muted text-muted-foreground";
  if (pct >= 2) return "bg-green-600/80 text-white dark:bg-green-600/70";
  if (pct >= 0.5) return "bg-green-500/50 text-green-900 dark:text-green-100";
  if (pct >= 0) return "bg-green-400/30 text-green-800 dark:text-green-200";
  if (pct >= -0.5) return "bg-red-400/30 text-red-800 dark:text-red-200";
  if (pct >= -2) return "bg-red-500/50 text-red-900 dark:text-red-100";
  return "bg-red-600/80 text-white dark:bg-red-600/70";
}

export function WorldHeatmap({ data, loading }: WorldHeatmapProps) {
  const { t } = useLocale();
  return (
    <Card data-testid="world-heatmap">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Globe className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("market.globalTrend")}
          <span className="ml-auto text-xs font-normal text-muted-foreground">{t("market.regionalReturn")}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="grid grid-cols-4 gap-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-muted/30" />
            ))}
          </div>
        )}

        {!loading && (
          <>
            {/* 지역별 히트맵 그리드 — 옵션 F-1 */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {data.map((country) => {
                const positive = !country.change_pct.startsWith("-");
                return (
                  <div
                    key={country.country_code}
                    className={cn(
                      "rounded-lg px-3 py-2.5 transition-opacity hover:opacity-90",
                      getHeatColor(country.change_pct),
                    )}
                    aria-label={`${country.country_name} ${country.change_pct}%`}
                  >
                    <p className="text-xs font-bold">{country.country_name}</p>
                    <p className="mt-0.5 text-lg font-bold tabular-nums">
                      {positive && !country.change_pct.startsWith("+") ? "+" : ""}
                      {country.change_pct}%
                    </p>
                    <p className="mt-0.5 truncate text-[10px] opacity-80">
                      {country.market_cap_usd}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* 범례 */}
            <div className="mt-3 flex items-center justify-end gap-1">
              <span className="text-[10px] text-muted-foreground">{t("market.legend.down")}</span>
              {["bg-red-600/70", "bg-red-500/50", "bg-red-400/30", "bg-green-400/30", "bg-green-500/50", "bg-green-600/70"].map(
                (cls, i) => (
                  <div key={i} className={cn("h-2.5 w-4 rounded-sm", cls)} aria-hidden="true" />
                ),
              )}
              <span className="text-[10px] text-muted-foreground">{t("market.legend.up")}</span>
            </div>

            {/* TODO: 옵션 F-2 — react-simple-maps 세계지도 구현 예정 */}
          </>
        )}
      </CardContent>
    </Card>
  );
}
