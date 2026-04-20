"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  listWatchlist,
  removeWatchlist,
  addWatchlist,
  type WatchlistItemCreate,
} from "@/lib/api/watchlist";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/empty-state";
import { AssetBadge } from "@/components/common/asset-badge";
import { Sparkline } from "@/components/watchlist/sparkline";
import { useTickersStore, makeTickerKey } from "@/stores/tickers";
import { useRealtimeTicker } from "@/lib/realtime/use-realtime-ticker";
import { type SymbolInfo } from "@/lib/api/symbols";
import { SymbolSearch } from "@/components/watchlist/symbol-search";
import { listHoldings } from "@/lib/api/portfolio";

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
};

function resolveAssetClass(item: { market: string }) {
  return ASSET_CLASS_MAP[item.market] ?? "macro";
}

function formatPrice(price: number, currency: string) {
  if (currency === "KRW") {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(price);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price);
}

function formatVolume(volume: number | undefined) {
  if (volume == null) return "-";
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  return String(volume);
}

export function WatchlistTable() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["watchlist"],
    queryFn: listWatchlist,
    staleTime: 10_000,
  });

  const deleteMutation = useMutation({
    mutationFn: removeWatchlist,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const addMutation = useMutation({
    mutationFn: addWatchlist,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  // 보유 종목 교차 표시용
  const { data: holdings } = useQuery({
    queryKey: ["portfolio", "holdings"],
    queryFn: listHoldings,
    staleTime: 30_000,
  });
  const holdingCodeSet = new Set(
    holdings?.map((h) => `${h.market}:${h.code}`) ?? [],
  );

  // WS 실시간 연결
  const symbols =
    data?.map((item) => ({ market: item.market, code: item.code })) ?? [];
  useRealtimeTicker(symbols);

  const tickers = useTickersStore((s) => s.tickers);

  function handleAddSymbol(symbolInfo: SymbolInfo) {
    const body: WatchlistItemCreate = {
      market: symbolInfo.market,
      code: symbolInfo.symbol,
    };
    addMutation.mutate(body);
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-full max-w-sm animate-pulse rounded-md bg-muted" />
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 w-full animate-pulse rounded-md bg-muted" />
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
        워치리스트를 불러오는 중 오류가 발생했습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <SymbolSearch onSelect={handleAddSymbol} />
        {addMutation.isPending && (
          <span className="text-xs text-muted-foreground">추가 중...</span>
        )}
        {addMutation.isError && (
          <span className="text-xs text-destructive">추가 실패</span>
        )}
      </div>

      {!data || data.length === 0 ? (
        <EmptyState
          title="워치리스트가 비어 있습니다"
          description="관심 종목을 검색해서 추가하면 실시간 시세를 확인할 수 있습니다."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>심볼</TableHead>
                <TableHead>자산군</TableHead>
                <TableHead className="text-right">현재가</TableHead>
                <TableHead className="text-right">등락률</TableHead>
                <TableHead className="text-right">거래량</TableHead>
                <TableHead>스파크라인</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item) => {
                const tickerKey = makeTickerKey(item.market, item.code);
                const ticker = tickers[tickerKey];
                const assetClass = resolveAssetClass(item);
                const currency =
                  item.market === "upbit" ? "KRW" : "USD";
                const price = ticker?.price;
                const changePct = ticker?.change_pct ?? 0;
                const volume = ticker?.volume;
                const isPositive = changePct >= 0;

                const isHolding = holdingCodeSet.has(
                  `${item.market}:${item.code}`,
                );
                return (
                  <TableRow
                    key={item.id}
                    data-testid="watchlist-row"
                    data-updated={ticker?.ts ?? undefined}
                  >
                    <TableCell>
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-1.5">
                          <Link
                            href={`/symbol/${encodeURIComponent(item.market)}/${encodeURIComponent(item.code)}`}
                            className="font-medium hover:underline focus:outline-none focus:ring-2 focus:ring-ring rounded"
                          >
                            {item.code}
                          </Link>
                          {isHolding && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-1.5 py-0"
                            >
                              보유 중
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {item.market}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <AssetBadge assetClass={assetClass} />
                    </TableCell>
                    <TableCell
                      className="text-right tabular-nums"
                      data-testid="realtime-price"
                    >
                      {price != null ? formatPrice(price, currency) : "-"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <span
                        className={
                          isPositive
                            ? "flex items-center justify-end gap-0.5 text-green-600 dark:text-green-400"
                            : "flex items-center justify-end gap-0.5 text-red-600 dark:text-red-400"
                        }
                      >
                        {isPositive ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            aria-hidden="true"
                          >
                            <path d="m5 12 7-7 7 7" />
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            aria-hidden="true"
                          >
                            <path d="m19 12-7 7-7-7" />
                          </svg>
                        )}
                        {Math.abs(changePct).toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatVolume(volume)}
                    </TableCell>
                    <TableCell>
                      <Sparkline market={item.market} code={item.code} />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        data-testid="watchlist-delete"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        aria-label={`${item.code} 삭제`}
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(item.id)}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          aria-hidden="true"
                        >
                          <path d="M3 6h18" />
                          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                        </svg>
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
