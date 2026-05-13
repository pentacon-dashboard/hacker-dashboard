"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Info,
  Trash2,
  CheckCircle,
  AlertCircle,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  resetPortfolioCustomerData,
  type PortfolioCustomerDataResetResponse,
} from "@/lib/api/portfolio";

interface SystemInfoProps {
  version?: string;
  apiStatus?: "healthy" | "degraded" | "error";
  buildTime?: string;
  cacheSizeMb?: number;
}

const RESET_CONFIRMATION = "CLEAR_CUSTOMER_DATA";
const STORAGE_KEYS_TO_KEEP = ["theme", "hd-theme", "hd-locale", "hd-accent"];

function clearLocalAppCache() {
  if (typeof window === "undefined") return;

  Object.keys(localStorage).forEach((k) => {
    if (!STORAGE_KEYS_TO_KEEP.includes(k)) localStorage.removeItem(k);
  });
  sessionStorage.clear();
}

export function SystemInfo({
  version = "0.3.1-sprint-08",
  apiStatus = "healthy",
  buildTime,
  cacheSizeMb = 42,
}: SystemInfoProps) {
  const [cacheCleared, setCacheCleared] = useState(false);
  const [resetConfirmation, setResetConfirmation] = useState("");
  const [resetPending, setResetPending] = useState(false);
  const [resetResult, setResetResult] =
    useState<PortfolioCustomerDataResetResponse | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { locale, t } = useLocale();

  const fmtLocale = locale === "en" ? "en-US" : "ko-KR";
  const formattedBuild = buildTime
    ? new Date(buildTime).toLocaleString(fmtLocale)
    : new Date().toLocaleString(fmtLocale);

  function handleClearCache() {
    queryClient.clear();
    clearLocalAppCache();
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 3000);
  }

  async function handleResetCustomerData() {
    if (resetConfirmation !== RESET_CONFIRMATION || resetPending) return;

    setResetPending(true);
    setResetError(null);
    setResetResult(null);

    try {
      const result = await resetPortfolioCustomerData(resetConfirmation);
      queryClient.clear();
      clearLocalAppCache();
      setResetResult(result);
      setResetConfirmation("");
    } catch (error) {
      setResetError(
        error instanceof Error
          ? error.message
          : t("settings.system.customerData.error"),
      );
    } finally {
      setResetPending(false);
    }
  }

  return (
    <Card data-testid="system-info">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Info className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("settings.system.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {[
          { label: t("settings.system.version"), value: version },
          { label: t("settings.system.buildTime"), value: formattedBuild },
          { label: t("settings.system.cacheSize"), value: `${cacheSizeMb} MB` },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{item.label}</span>
            <span className="text-xs font-mono font-medium">{item.value}</span>
          </div>
        ))}

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t("settings.system.apiStatus")}</span>
          <div className="flex items-center gap-1.5">
            {apiStatus === "healthy" ? (
              <>
                <CheckCircle className="h-3.5 w-3.5 text-green-500" aria-hidden="true" />
                <span className="text-xs font-medium text-green-500">{t("settings.system.healthy")}</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
                <span className="text-xs font-medium text-destructive">
                  {apiStatus === "degraded" ? t("settings.system.degraded") : t("settings.system.error")}
                </span>
              </>
            )}
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={handleClearCache}
          data-testid="clear-cache-btn"
        >
          {cacheCleared ? (
            <>
              <CheckCircle className="mr-2 h-3.5 w-3.5 text-green-500" aria-hidden="true" />
              {t("settings.system.cacheCleared")}
            </>
          ) : (
            <>
              <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
              {t("settings.system.clearCache")}
            </>
          )}
        </Button>

        <p className="text-[11px] leading-4 text-muted-foreground">
          {t("settings.system.clearCacheDesc")}
        </p>

        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <div className="flex items-start gap-2">
            <ShieldAlert
              className="mt-0.5 h-4 w-4 shrink-0 text-destructive"
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1 space-y-2">
              <div>
                <p className="text-xs font-semibold text-destructive">
                  {t("settings.system.customerData.title")}
                </p>
                <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
                  {t("settings.system.customerData.desc")}
                </p>
              </div>

              <input
                aria-label={t("settings.system.customerData.confirmLabel")}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-xs outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                data-testid="reset-customer-data-confirmation"
                value={resetConfirmation}
                onChange={(event) => setResetConfirmation(event.target.value)}
                placeholder={RESET_CONFIRMATION}
                autoComplete="off"
              />

              <Button
                variant="destructive"
                size="sm"
                className="w-full"
                onClick={handleResetCustomerData}
                disabled={
                  resetConfirmation !== RESET_CONFIRMATION || resetPending
                }
                data-testid="reset-customer-data-btn"
              >
                {resetPending ? (
                  <>
                    <Loader2
                      className="mr-2 h-3.5 w-3.5 animate-spin"
                      aria-hidden="true"
                    />
                    {t("settings.system.customerData.resetting")}
                  </>
                ) : (
                  <>
                    <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                    {t("settings.system.customerData.action")}
                  </>
                )}
              </Button>

              {resetResult ? (
                <p
                  className="text-[11px] leading-4 text-destructive"
                  data-testid="reset-customer-data-result"
                >
                  {t("settings.system.customerData.result", {
                    holdings: resetResult.deleted_holdings,
                    clients: resetResult.deleted_clients,
                    snapshots: resetResult.deleted_snapshots,
                  })}
                </p>
              ) : null}

              {resetError ? (
                <p
                  className="text-[11px] leading-4 text-destructive"
                  data-testid="reset-customer-data-error"
                >
                  {t("settings.system.customerData.error")}: {resetError}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
