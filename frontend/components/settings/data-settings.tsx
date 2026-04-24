"use client";

import { Database } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { useLocale } from "@/lib/i18n/locale-provider";

export interface DataConfig {
  refresh_interval_sec: number;
  auto_refresh: boolean;
  auto_backup: boolean;
  cache_size_mb: number;
}

interface DataSettingsProps {
  config: DataConfig;
  onChange: (config: DataConfig) => void;
}

const REFRESH_OPTIONS = [10, 30, 60, 120, 300];

export function DataSettings({ config, onChange }: DataSettingsProps) {
  const { locale, t } = useLocale();

  function update<K extends keyof DataConfig>(key: K, value: DataConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  function formatInterval(sec: number): string {
    if (locale === "en") {
      return sec < 60 ? `${sec}s` : `${sec / 60}min`;
    }
    return sec < 60 ? `${sec}초` : `${sec / 60}분`;
  }

  return (
    <Card data-testid="data-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Database className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("settings.data.title")}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{t("settings.data.desc")}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="refresh-select">
            {t("settings.data.refreshInterval")}
          </label>
          <select
            id="refresh-select"
            value={config.refresh_interval_sec}
            onChange={(e) => update("refresh_interval_sec", Number(e.target.value))}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label={t("settings.data.refreshInterval")}
          >
            {REFRESH_OPTIONS.map((sec) => (
              <option key={sec} value={sec}>
                {formatInterval(sec)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">{t("settings.data.autoRefresh")}</p>
            <p className="text-xs text-muted-foreground">{t("settings.data.autoRefreshDesc")}</p>
          </div>
          <Switch
            checked={config.auto_refresh}
            onCheckedChange={(v) => update("auto_refresh", v)}
            aria-label={t("settings.data.autoRefresh")}
          />
        </div>

        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">{t("settings.data.autoBackup")}</p>
            <p className="text-xs text-muted-foreground">{t("settings.data.autoBackupDesc")}</p>
          </div>
          <Switch
            checked={config.auto_backup}
            onCheckedChange={(v) => update("auto_backup", v)}
            aria-label={t("settings.data.autoBackup")}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-muted-foreground">{t("settings.data.cacheSize")}</label>
            <span className="text-xs font-mono text-foreground">{config.cache_size_mb} MB</span>
          </div>
          <Slider
            min={32}
            max={512}
            step={32}
            value={config.cache_size_mb}
            onValueChange={(v) => update("cache_size_mb", v)}
            aria-label={t("settings.data.cacheSize")}
          />
          <div className="flex justify-between text-xs text-muted-foreground/60">
            <span>32 MB</span>
            <span>512 MB</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
