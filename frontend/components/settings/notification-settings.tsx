"use client";

import { Bell } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

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
  function update<K extends keyof NotificationConfig>(key: K, value: NotificationConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  const items = [
    {
      key: "email_alerts" as const,
      label: "이메일 알림",
      desc: "중요 포트폴리오 변동 시 이메일 발송",
    },
    {
      key: "push_alerts" as const,
      label: "푸시 알림",
      desc: "브라우저 푸시 알림 활성화",
    },
    {
      key: "daily_digest" as const,
      label: "일일 다이제스트",
      desc: "매일 오전 8시 일간 요약 발송",
    },
  ];

  return (
    <Card data-testid="notification-settings">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
          알림 설정
        </CardTitle>
        <p className="text-xs text-muted-foreground">알림 채널 및 임계값을 설정합니다</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => (
          <div
            key={item.key}
            className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2"
          >
            <div>
              <p className="text-xs font-medium">{item.label}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
            <Switch
              checked={config[item.key]}
              onCheckedChange={(v) => update(item.key, v)}
              aria-label={item.label}
            />
          </div>
        ))}

        {/* 가격 알림 임계값 */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="price-threshold">
            가격 알림 임계값 (%)
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
              aria-label="가격 알림 임계값"
            />
            <span className="text-xs text-muted-foreground">
              ±{config.price_threshold_pct}% 변동 시 알림
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
