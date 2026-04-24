"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Info, Trash2, CheckCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-provider";

interface SystemInfoProps {
  version?: string;
  apiStatus?: "healthy" | "degraded" | "error";
  buildTime?: string;
  cacheSizeMb?: number;
}

export function SystemInfo({
  version = "0.3.1-sprint-08",
  apiStatus = "healthy",
  buildTime,
  cacheSizeMb = 42,
}: SystemInfoProps) {
  const [cacheCleared, setCacheCleared] = useState(false);
  const queryClient = useQueryClient();
  const { locale, t } = useLocale();

  const fmtLocale = locale === "en" ? "en-US" : "ko-KR";
  const formattedBuild = buildTime
    ? new Date(buildTime).toLocaleString(fmtLocale)
    : new Date().toLocaleString(fmtLocale);

  function handleClearCache() {
    queryClient.clear();
    if (typeof window !== "undefined") {
      const keysToKeep = ["theme", "hd-theme", "hd-locale", "hd-accent"];
      Object.keys(localStorage).forEach((k) => {
        if (!keysToKeep.includes(k)) localStorage.removeItem(k);
      });
    }
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 3000);
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
      </CardContent>
    </Card>
  );
}
