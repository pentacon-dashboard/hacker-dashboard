"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

// BE /market/commodities 실제 스키마
export interface CommodityItem {
  symbol: string;
  name: string;
  price: string;
  change_pct: string;
  unit: string;
}

interface CommodityPanelProps {
  commodities: CommodityItem[];
  loading?: boolean;
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
            const positive = !c.change_pct.startsWith("-");
            return (
              <div
                key={c.symbol}
                className="flex items-center gap-3 rounded-lg border border-border bg-card/50 px-3 py-2"
                data-testid={`commodity-${c.symbol}`}
              >
                {/* 이름 */}
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold">{c.name}</p>
                  <p className="text-[10px] text-muted-foreground">{c.unit}</p>
                </div>

                {/* 가격 + 변동 */}
                <div className="text-right">
                  <p className="text-sm font-bold tabular-nums">{c.price}</p>
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
                    {positive && !c.change_pct.startsWith("+") ? "+" : ""}
                    {c.change_pct}%
                  </p>
                </div>
              </div>
            );
          })}
      </CardContent>
    </Card>
  );
}
