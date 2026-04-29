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
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getSymbolDisplayParts,
  isDomesticStockMarket,
} from "@/lib/market/display";

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
  krx: "stock",
  kiwoom: "stock",
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
  const { t } = useLocale();
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
        {t("watchlist.error")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <SymbolSearch onSelect={handleAddSymbol} />
        {addMutation.isPending && (
          <span className="text-xs text-muted-foreground">{t("watchlist.adding")}</span>
        )}
        {addMutation.isError && (
          <span className="text-xs text-destructive">{t("watchlist.addFailed")}</span>
        )}
      </div>

      {!data || data.length === 0 ? (
        <EmptyState
          title={t("watchlist.empty.title")}
          description={t("watchlist.empty.desc")}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("watchlist.col.symbol")}</TableHead>
                <TableHead>{t("watchlist.col.assetClass")}</TableHead>
                <TableHead className="text-right">{t("watchlist.col.price")}</TableHead>
                <TableHead className="text-right">{t("watchlist.col.change")}</TableHead>
                <TableHead className="text-right">{t("watchlist.col.volume")}</TableHead>
                <TableHead>{t("watchlist.col.sparkline")}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item) => {
                const tickerKey = makeTickerKey(item.market, item.code);
                const ticker = tickers[tickerKey];
                const assetClass = resolveAssetClass(item);
                const currency =
                  item.market === "upbit" || isDomesticStockMarket(item.market)
                    ? "KRW"
                    : "USD";
                const price = ticker?.price;
                const changePct = ticker?.change_pct ?? 0;
                const volume = ticker?.volume;
                const isPositive = changePct >= 0;
                const displayParts = getSymbolDisplayParts(item.market, item.code);
                const displaySymbol = displayParts.primary;

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
                            title={displayParts.secondary ?? displayParts.normalizedCode}
                          >
                            {displaySymbol}
                          </Link>
                          {isHolding && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-1.5 py-0"
                            >
                              {t("watchlist.holding")}
                            </Badge>
                          )}
                        </div>
                        {displayParts.secondary ? (
                          <div className="text-xs text-muted-foreground">
                            {displayParts.secondary}
                          </div>
                        ) : null}
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
                        aria-label={`${displaySymbol} ${t("table.delete")}`}
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
