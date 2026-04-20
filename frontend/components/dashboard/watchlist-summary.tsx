"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listWatchlist } from "@/lib/api/watchlist";
import { useTickersStore, makeTickerKey } from "@/stores/tickers";
import { useRealtimeTicker } from "@/lib/realtime/use-realtime-ticker";
import { AssetBadge } from "@/components/common/asset-badge";
import { AssetPie } from "@/components/dashboard/asset-pie";
import { EmptyState } from "@/components/common/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
};

const PIE_COLORS: Record<string, string> = {
  crypto: "#f97316",
  stock: "#3b82f6",
  fx: "#8b5cf6",
  macro: "#6b7280",
};

export function WatchlistSummary() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["watchlist"],
    queryFn: listWatchlist,
    staleTime: 10_000,
  });

  const top5 = data?.slice(0, 5) ?? [];
  const symbols = top5.map((item) => ({ market: item.market, code: item.code }));
  useRealtimeTicker(symbols);

  const tickers = useTickersStore((s) => s.tickers);

  // 자산군 분포 계산
  const assetClassCount: Record<string, number> = {};
  for (const item of data ?? []) {
    const ac = ASSET_CLASS_MAP[item.market] ?? "macro";
    assetClassCount[ac] = (assetClassCount[ac] ?? 0) + 1;
  }
  const pieData = Object.entries(assetClassCount).map(([name, value]) => ({
    name,
    value,
    color: PIE_COLORS[name] ?? "#6b7280",
  }));

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg border bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive"
      >
        워치리스트 데이터를 불러올 수 없습니다.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="워치리스트가 비어 있습니다"
        description="워치리스트에 종목을 추가하면 여기에 요약이 표시됩니다."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 상위 5개 요약 카드 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {top5.map((item) => {
          const key = makeTickerKey(item.market, item.code);
          const ticker = tickers[key];
          const price = ticker?.price;
          const changePct = ticker?.change_pct ?? 0;
          const isPositive = changePct >= 0;
          const assetClass = ASSET_CLASS_MAP[item.market] ?? "macro";

          return (
            <Link
              key={item.id}
              href={`/symbol/${encodeURIComponent(item.market)}/${encodeURIComponent(item.code)}`}
              className="block focus:outline-none focus:ring-2 focus:ring-ring rounded-lg"
            >
              <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
                <CardHeader className="pb-1 pt-3 px-3">
                  <CardTitle className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                    <span className="truncate">{item.code}</span>
                    <AssetBadge assetClass={assetClass} className="text-[10px] px-1.5 py-0" />
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-3 pb-3">
                  <div className="text-lg font-bold tabular-nums">
                    {price != null
                      ? item.market === "upbit"
                        ? new Intl.NumberFormat("ko-KR", {
                            style: "currency",
                            currency: "KRW",
                            maximumFractionDigits: 0,
                          }).format(price)
                        : `$${price.toFixed(2)}`
                      : "-"}
                  </div>
                  <div
                    className={
                      isPositive
                        ? "text-xs text-green-600 dark:text-green-400"
                        : "text-xs text-red-600 dark:text-red-400"
                    }
                  >
                    {isPositive ? "+" : ""}
                    {changePct.toFixed(2)}%
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* 자산군 분포 파이 */}
      {pieData.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="mb-3 text-sm font-semibold">자산군 분포</h3>
          <AssetPie data={pieData} />
        </div>
      )}
    </div>
  );
}
