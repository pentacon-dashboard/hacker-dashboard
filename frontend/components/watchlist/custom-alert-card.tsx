"use client";

import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getAlerts, createAlert, type AlertCreate } from "@/lib/api/watchlist";
import { listWatchlist } from "@/lib/api/watchlist";
import { useLocale } from "@/lib/i18n/locale-provider";
import { formatSymbolDisplay } from "@/lib/market/display";

/**
 * CustomAlertCard — 사용자 맞춤 알림 규칙을 세밀하게 만들기 위한 카드.
 * - 워치리스트 종목 선택 드롭다운
 * - direction(above/below), threshold(number), notes(free-text, optional)
 * - 생성 시 BE /watchlist/alerts POST
 */
export function CustomAlertCard() {
  const { t } = useLocale();
  const queryClient = useQueryClient();

  const { data: watchlistItems } = useQuery({
    queryKey: ["watchlist"],
    queryFn: listWatchlist,
    staleTime: 30_000,
  });

  const { data: alerts } = useQuery({
    queryKey: ["watchlist", "alerts"],
    queryFn: getAlerts,
    staleTime: 10_000,
  });

  const [symbol, setSymbol] = useState("");
  const [direction, setDirection] = useState<"above" | "below">("above");
  const [threshold, setThreshold] = useState<string>("");

  const createMutation = useMutation({
    mutationFn: (payload: AlertCreate) => createAlert(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist", "alerts"] });
      setThreshold("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol || !threshold) return;
    const [market, code] = symbol.split("|");
    const t = parseFloat(threshold);
    if (isNaN(t) || t <= 0) return;
    createMutation.mutate({
      symbol: code ?? symbol,
      market: market ?? "yahoo",
      direction,
      threshold: t,
    });
  }

  const items = watchlistItems ?? [];
  const totalAlerts = alerts?.length ?? 0;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" data-testid="custom-alert-form">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground" htmlFor="ca-symbol">
          {t("table.symbol")}
        </label>
        <select
          id="ca-symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          required
        >
          <option value="">— {t("watchlist.title")} —</option>
          {items.map((i) => (
            <option key={i.id} value={`${i.market}|${i.code}`}>
              {formatSymbolDisplay(i.market, i.code)}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="ca-direction">
            {t("watchlist.direction.above")} / {t("watchlist.direction.below")}
          </label>
          <select
            id="ca-direction"
            value={direction}
            onChange={(e) => setDirection(e.target.value as "above" | "below")}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="above">{t("watchlist.direction.above")}</option>
            <option value="below">{t("watchlist.direction.below")}</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="ca-threshold">
            {t("watchlist.threshold")}
          </label>
          <input
            id="ca-threshold"
            type="number"
            step="any"
            min="0"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            placeholder="0.00"
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            required
          />
        </div>
      </div>

      <Button
        type="submit"
        size="sm"
        disabled={createMutation.isPending || !symbol || !threshold}
        className="gap-1.5"
      >
        <Plus className="h-3.5 w-3.5" />
        {t("watchlist.addAlert")}
      </Button>

      {createMutation.isError && (
        <p className="text-xs text-destructive">{t("common.error")}</p>
      )}
      {createMutation.isSuccess && !createMutation.isPending && (
        <p className="text-xs text-green-500">✓ {totalAlerts}</p>
      )}
    </form>
  );
}
