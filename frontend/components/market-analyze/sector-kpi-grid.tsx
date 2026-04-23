"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectorData {
  sector: string;
  change_pct: number;
  market_cap_b?: number;
}

interface SectorKpiGridProps {
  sectors: SectorData[];
  loading?: boolean;
}

export function SectorKpiGrid({ sectors, loading }: SectorKpiGridProps) {
  return (
    <Card data-testid="sector-kpi-grid">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <BarChart3 className="h-4 w-4 text-primary" aria-hidden="true" />
          섹터별 등락률
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
            const positive = sector.change_pct >= 0;
            const barPct = Math.min(Math.abs(sector.change_pct) * 25, 100);
            return (
              <div
                key={sector.sector}
                className="flex items-center gap-2"
                data-testid={`sector-${sector.sector}`}
              >
                {/* 섹터명 */}
                <span className="w-28 shrink-0 truncate text-xs text-muted-foreground">
                  {sector.sector}
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
                  {positive ? "+" : ""}
                  {sector.change_pct.toFixed(2)}%
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
