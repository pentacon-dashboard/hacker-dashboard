"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

// BE가 한국어로 내려주는 섹터명 → i18n 키 매핑 테이블
const SECTOR_KEY_MAP: Record<string, string> = {
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
  change_pct: string;
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
    <Card data-testid="sector-kpi-grid">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <BarChart3 className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("market.sectorReturn")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {loading && (
          <div className="space-y-1">
            {[...Array(11)].map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted/20" />
            ))}
          </div>
        )}

        {!loading &&
          sectors.map((sector) => {
            const positive = !sector.change_pct.startsWith("-");
            const numPct = parseFloat(sector.change_pct);
            const barPct = Math.min(Math.abs(isNaN(numPct) ? 0 : numPct) * 25, 100);
            const sectorKey = SECTOR_KEY_MAP[sector.name];
            const sectorLabel = sectorKey ? t(sectorKey) : sector.name;
            return (
              <div
                key={sector.name}
                className="flex items-center gap-2"
                data-testid={`sector-${sector.name}`}
              >
                {/* 섹터명 */}
                <span className="w-28 shrink-0 truncate text-xs text-muted-foreground">
                  {sectorLabel}
                </span>

                {/* 바 */}
                <div className="flex flex-1 items-center">
                  <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted/30">
                    <div
                      className={cn(
                        "absolute top-0 h-full rounded",
                        positive ? "bg-green-500/40 left-0" : "bg-destructive/40 right-0",
                      )}
                      style={{ width: `${barPct}%` }}
                      aria-hidden="true"
                    />
                  </div>
                </div>

                {/* 수치 */}
                <span
                  className={cn(
                    "w-14 shrink-0 text-right text-xs font-bold tabular-nums",
                    positive ? "text-green-500" : "text-destructive",
                  )}
                >
                  {positive && !sector.change_pct.startsWith("+") ? "+" : ""}
                  {sector.change_pct}%
                </span>

                {positive ? (
                  <TrendingUp className="h-3 w-3 shrink-0 text-green-500" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3 shrink-0 text-destructive" aria-hidden="true" />
                )}
              </div>
            );
          })}
      </CardContent>
    </Card>
  );
}
