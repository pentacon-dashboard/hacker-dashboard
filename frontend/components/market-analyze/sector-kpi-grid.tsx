"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  formatSignedPercent,
  isNonNegativePercent,
  parsePercent,
  type PercentValue,
} from "@/components/market-analyze/percent";

// BE가 한국어로 내려주는 섹터명 → i18n 키 매핑 테이블
const SECTOR_KEY_MAP: Record<string, string> = {
  "Information Technology": "market.sector.it",
  Technology: "market.sector.it",
  Semiconductor: "market.sector.semiconductor",
  Financials: "market.sector.finance",
  Healthcare: "market.sector.health",
  Energy: "market.sector.energy",
  "Consumer Disc.": "market.sector.consumer",
  "Consumer Discretionary": "market.sector.consumer",
  "Consumer Staples": "market.sector.consumer",
  Industrials: "market.sector.industrial",
  Materials: "market.sector.materials",
  Utilities: "market.sector.utilities",
  "Real Estate": "market.sector.realEstate",
  Communication: "market.sector.telecom",
  "Communication Services": "market.sector.telecom",
  "정보기술": "market.sector.it",
  "반도체": "market.sector.semiconductor",
  "금융": "market.sector.finance",
  "헬스케어": "market.sector.health",
  "에너지": "market.sector.energy",
  "소비재": "market.sector.consumer",
  "산업재": "market.sector.industrial",
  "소재": "market.sector.materials",
  "유틸리티": "market.sector.utilities",
  "부동산": "market.sector.realEstate",
  "통신": "market.sector.telecom",
};

// BE /market/sectors 실제 스키마
export interface SectorItem {
  name: string;
  change_pct: PercentValue;
  constituents: number;
  leaders: string[];
}

interface SectorKpiGridProps {
  sectors: SectorItem[];
  loading?: boolean;
}

export function SectorKpiGrid({ sectors, loading }: SectorKpiGridProps) {
  const { t } = useLocale();
  return (
    <Card data-testid="sector-kpi-grid" className="flex h-full min-h-[21rem] flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <BarChart3 className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("market.sectorReturn")}
        </CardTitle>
      </CardHeader>
      <CardContent
        className="grid flex-1 auto-rows-fr gap-1.5 sm:gap-2"
        data-testid="sector-kpi-list"
      >
        {loading && (
          <>
            {[...Array(11)].map((_, i) => (
              <div key={i} className="min-h-8 animate-pulse rounded-md bg-muted/20" />
            ))}
          </>
        )}

        {!loading &&
          sectors.map((sector) => {
            const positive = isNonNegativePercent(sector.change_pct);
            const numPct = parsePercent(sector.change_pct);
            const barPct = Math.min(Math.abs(isNaN(numPct) ? 0 : numPct) * 25, 100);
            const sectorKey = SECTOR_KEY_MAP[sector.name];
            const sectorLabel = sectorKey ? t(sectorKey) : sector.name;
            const changeLabel = formatSignedPercent(sector.change_pct);
            return (
              <div
                key={sector.name}
                className="grid min-h-8 grid-cols-[minmax(4.75rem,6.5rem)_minmax(3.5rem,1fr)_4.25rem_0.875rem] items-center gap-1.5 rounded-md px-1 py-1 transition-colors hover:bg-muted/20 sm:grid-cols-[minmax(5.5rem,7rem)_minmax(5rem,1fr)_4.75rem_1rem] sm:gap-2 sm:px-2"
                data-testid={`sector-${sector.name}`}
                role="group"
                aria-label={`${sectorLabel} ${changeLabel}`}
              >
                {/* 섹터명 */}
                <span className="min-w-0 truncate text-[11px] font-medium text-muted-foreground sm:text-xs">
                  {sectorLabel}
                </span>

                {/* 바 */}
                <div
                  className="relative h-5 min-w-0 overflow-hidden rounded bg-muted/30"
                  data-testid={`sector-bar-${sector.name}`}
                >
                  <div
                    className={cn(
                      "absolute top-0 h-full rounded",
                      positive ? "bg-green-500/40 left-0" : "bg-destructive/40 right-0",
                    )}
                    style={{ width: `${barPct}%` }}
                    aria-hidden="true"
                  />
                </div>

                {/* 수치 */}
                <span
                  className={cn(
                    "text-right text-xs font-bold tabular-nums leading-none sm:text-[13px]",
                    positive ? "text-green-500" : "text-destructive",
                  )}
                >
                  {changeLabel}
                </span>

                {positive ? (
                  <TrendingUp className="h-3.5 w-3.5 justify-self-end text-green-500" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5 justify-self-end text-destructive" aria-hidden="true" />
                )}
              </div>
            );
          })}
      </CardContent>
    </Card>
  );
}
