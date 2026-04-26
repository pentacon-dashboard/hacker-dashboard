"use client";

import { Bell } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { useLocale } from "@/lib/i18n/locale-provider";

export interface NotificationConfig {
  email_alerts: boolean;
  push_alerts: boolean;
  price_threshold_pct: number;
  daily_digest: boolean;
}

interface NotificationSettingsProps {
  config: NotificationConfig;
  onChange: (config: NotificationConfig) => void;
}

export function NotificationSettings({ config, onChange }: NotificationSettingsProps) {
  const { t } = useLocale();

  function update<K extends keyof NotificationConfig>(key: K, value: NotificationConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  const items = [
    { key: "email_alerts" as const, labelKey: "settings.notifications.email", descKey: "settings.notifications.emailDesc" },
    { key: "push_alerts" as const, labelKey: "settings.notifications.push", descKey: "settings.notifications.pushDesc" },
    { key: "daily_digest" as const, labelKey: "settings.notifications.daily", descKey: "settings.notifications.dailyDesc" },
  ];

  return (
    <Card data-testid="notification-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
          {t("settings.notifications.title")}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{t("settings.notifications.desc")}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => (
          <div
            key={item.key}
            className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2"
          >
            <div>
              <p className="text-xs font-medium">{t(item.labelKey)}</p>
              <p className="text-xs text-muted-foreground">{t(item.descKey)}</p>
            </div>
            <Switch
              checked={config[item.key]}
              onCheckedChange={(v) => update(item.key, v)}
              aria-label={t(item.labelKey)}
            />
          </div>
        ))}

        {/* 가격 알림 임계값 */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="price-threshold">
            {t("settings.notifications.threshold")}
          </label>
          <div className="flex items-center gap-2">
            <input
              id="price-threshold"
              type="number"
              min={0.5}
              max={50}
              step={0.5}
              value={config.price_threshold_pct}
              onChange={(e) => update("price_threshold_pct", parseFloat(e.target.value) || 5)}
              className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              aria-label={t("settings.notifications.threshold")}
            />
            <span className="text-xs text-muted-foreground">
              {t("settings.notifications.thresholdHint", { n: config.price_threshold_pct })}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
