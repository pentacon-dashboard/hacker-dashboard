"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface CommodityData {
  code: string;
  name: string;
  value: number;
  unit: string;
  change_pct: number;
  sparkline: number[];
}

interface CommodityPanelProps {
  commodities: CommodityData[];
  loading?: boolean;
}

function MiniSparkline({ data, positive }: { data: number[]; positive: boolean }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 48;
  const h = 20;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline
        points={pts}
        fill="none"
        stroke={positive ? "rgb(34 197 94)" : "rgb(239 68 68)"}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CommodityPanel({ commodities, loading }: CommodityPanelProps) {
  return (
    <Card data-testid="commodity-panel">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Layers className="h-4 w-4 text-primary" aria-hidden="true" />
          원자재
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading && (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-muted/20" />
            ))}
          </div>
        )}

        {!loading &&
          commodities.map((c) => {
            const positive = c.change_pct >= 0;
            return (
              <div
                key={c.code}
                className="flex items-center gap-3 rounded-lg border border-border bg-card/50 px-3 py-2"
                data-testid={`commodity-${c.code}`}
              >
                {/* 이름 */}
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold">{c.name}</p>
                  <p className="text-[10px] text-muted-foreground">{c.unit}</p>
                </div>

                {/* 스파크라인 */}
                <MiniSparkline data={c.sparkline} positive={positive} />

                {/* 가격 + 변동 */}
                <div className="text-right">
                  <p className="text-sm font-bold tabular-nums">{c.value.toFixed(2)}</p>
                  <p
                    className={cn(
                      "flex items-center justify-end gap-0.5 text-xs font-semibold",
                      positive ? "text-green-500" : "text-destructive",
                    )}
                  >
                    {positive ? (
                      <TrendingUp className="h-3 w-3" aria-hidden="true" />
                    ) : (
                      <TrendingDown className="h-3 w-3" aria-hidden="true" />
                    )}
                    {positive ? "+" : ""}
                    {c.change_pct.toFixed(2)}%
                  </p>
                </div>
              </div>
            );
          })}
      </CardContent>
    </Card>
  );
}
