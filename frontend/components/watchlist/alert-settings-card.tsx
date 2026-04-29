"use client";

import { useState } from "react";
import { Bell, BellOff, Plus, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getAlerts,
  createAlert,
  updateAlert,
  deleteAlert,
  listWatchlist,
  type WatchlistAlert,
  type AlertCreate,
  type WatchlistItemResponse,
} from "@/lib/api/watchlist";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getSymbolDisplayParts,
  isValidSymbolCode,
} from "@/lib/market/display";

const QUERY_KEY = ["watchlist", "alerts"] as const;

function AlertRow({ alert }: { alert: WatchlistAlert }) {
  const { t } = useLocale();
  const qc = useQueryClient();
  const hasValidSymbol = isValidSymbolCode(alert.market, alert.symbol);
  const displayParts = hasValidSymbol
    ? getSymbolDisplayParts(alert.market, alert.symbol)
    : null;
  const displayLabel = hasValidSymbol
    ? displayParts?.primary ?? alert.symbol
    : t("watchlist.alert.corrupted", { id: alert.id });

  const toggleMutation = useMutation({
    mutationFn: () =>
      updateAlert(alert.id, { enabled: !alert.enabled }),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: QUERY_KEY });
      const prev = qc.getQueryData<WatchlistAlert[]>(QUERY_KEY);
      qc.setQueryData<WatchlistAlert[]>(QUERY_KEY, (old) =>
        (old ?? []).map((r) =>
          r.id === alert.id ? { ...r, enabled: !r.enabled } : r,
        ),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(QUERY_KEY, ctx.prev);
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteAlert(alert.id),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: QUERY_KEY });
      const prev = qc.getQueryData<WatchlistAlert[]>(QUERY_KEY);
      qc.setQueryData<WatchlistAlert[]>(QUERY_KEY, (old) =>
        (old ?? []).filter((r) => r.id !== alert.id),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(QUERY_KEY, ctx.prev);
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  const threshold = Number(alert.threshold);

  return (
    <li
      className="flex items-center justify-between rounded-lg border p-2"
      data-testid={`alert-rule-${alert.id}`}
    >
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium">{displayLabel}</p>
        {hasValidSymbol && displayParts?.secondary ? (
          <p className="text-[10px] text-muted-foreground">
            {displayParts.secondary}
          </p>
        ) : null}
        <p className="text-[10px] text-muted-foreground">
          {hasValidSymbol
            ? `${alert.direction === "above" ? t("watchlist.direction.above") : t("watchlist.direction.below")} ${threshold.toLocaleString("ko-KR")}`
            : t("watchlist.alert.corruptedHint")}
        </p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {hasValidSymbol && (
          <button
            type="button"
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isPending}
            aria-label={`${displayLabel} ${t(alert.enabled ? "watchlist.alert.toggleOff" : "watchlist.alert.toggleOn")}`}
            className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors ${
              alert.enabled
                ? "bg-primary/10 text-primary hover:bg-primary/20"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {alert.enabled ? (
              <Bell className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <BellOff className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </button>
        )}

        <button
          type="button"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          aria-label={`${displayLabel} ${t("watchlist.alert.delete")}`}
          className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
    </li>
  );
}

interface AddAlertFormProps {
  onClose: () => void;
  watchlistItems: WatchlistItemResponse[];
}

function AddAlertForm({ onClose, watchlistItems }: AddAlertFormProps) {
  const { t } = useLocale();
  const qc = useQueryClient();
  const [selection, setSelection] = useState("");
  const [direction, setDirection] = useState<"above" | "below">("above");
  const [threshold, setThreshold] = useState("");

  const createMutation = useMutation({
    mutationFn: (body: AlertCreate) => createAlert(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const thresholdNum = Number(threshold);
    if (!selection || !Number.isFinite(thresholdNum) || thresholdNum <= 0)
      return;
    const [market, symbol] = selection.split("|");
    if (!market || !symbol) return;
    createMutation.mutate({
      symbol,
      market,
      direction,
      threshold: thresholdNum,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-2 rounded-lg border bg-muted/30 p-3"
      data-testid="add-alert-form"
    >
      <select
        value={selection}
        onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
          setSelection(e.target.value)
        }
        className="h-7 w-full rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
        aria-label={t("watchlist.alert.ticker")}
        required
      >
        <option value="">{t("watchlist.alert.ticker")}</option>
        {watchlistItems.map((item) => (
          <option key={item.id} value={`${item.market}|${item.code}`}>
            {getSymbolDisplayParts(item.market, item.code).primary}
          </option>
        ))}
      </select>

      <div className="flex gap-2">
        <select
          value={direction}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setDirection(e.target.value as "above" | "below")
          }
          className="h-7 flex-1 rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={t("watchlist.threshold")}
        >
          <option value="above">{t("watchlist.alert.above")}</option>
          <option value="below">{t("watchlist.alert.below")}</option>
        </select>
        <input
          type="number"
          placeholder={t("watchlist.alert.basePrice")}
          value={threshold}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setThreshold(e.target.value)
          }
          className="h-7 flex-1 rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={t("watchlist.alert.basePrice")}
          min={0}
          step="any"
          required
        />
      </div>

      {watchlistItems.length === 0 ? (
        <p className="text-[10px] text-muted-foreground">
          {t("watchlist.empty.desc")}
        </p>
      ) : null}

      {createMutation.isError && (
        <p className="text-[10px] text-destructive" role="alert">
          {t("watchlist.alertAddFail")}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 text-xs"
          onClick={onClose}
        >
          {t("watchlist.alert.cancel")}
        </Button>
        <Button
          type="submit"
          size="sm"
          className="h-6 text-xs"
          disabled={createMutation.isPending || watchlistItems.length === 0}
        >
          {createMutation.isPending ? t("watchlist.alert.saving") : t("watchlist.alert.save")}
        </Button>
      </div>
    </form>
  );
}

export function AlertSettingsCard() {
  const { t } = useLocale();
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: getAlerts,
    staleTime: 30_000,
  });
  const watchlistQuery = useQuery({
    queryKey: ["watchlist"],
    queryFn: listWatchlist,
    staleTime: 30_000,
  });
  const alerts = data ?? [];
  const invalidAlertCount = alerts.filter(
    (alert) => !isValidSymbolCode(alert.market, alert.symbol),
  ).length;
  const orderedAlerts = [
    ...alerts.filter((alert) => isValidSymbolCode(alert.market, alert.symbol)),
    ...alerts.filter((alert) => !isValidSymbolCode(alert.market, alert.symbol)),
  ];

  return (
    <div className="space-y-3" data-testid="alert-settings-card">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold">{t("watchlist.alert.title")}</h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          aria-label={t("watchlist.addAlert")}
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus className="h-3 w-3" />
          {t("watchlist.add")}
        </Button>
      </div>

      {showForm && (
        <AddAlertForm
          onClose={() => setShowForm(false)}
          watchlistItems={watchlistQuery.data ?? []}
        />
      )}

      {invalidAlertCount > 0 && (
        <p className="text-[10px] text-amber-700">
          {t("watchlist.alert.corruptedCount", { n: invalidAlertCount })}
        </p>
      )}

      {isLoading ? (
        <div className="space-y-2" data-testid="alert-rules-loading">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid="alert-rules-error"
        >
          {t("watchlist.alertsError")}
        </p>
      ) : alerts.length === 0 ? (
        <p
          className="text-xs text-muted-foreground"
          data-testid="alert-rules-empty"
        >
          {t("watchlist.alertsEmpty")}
        </p>
      ) : (
        <ul className="space-y-2" data-testid="alert-rules-list">
          {orderedAlerts.map((alert) => (
            <AlertRow key={alert.id} alert={alert} />
          ))}
        </ul>
      )}
    </div>
  );
}
