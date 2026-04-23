"use client";

import { useCallback, useEffect, useState } from "react";
import { GeneralSettings } from "@/components/settings/general-settings";
import { NotificationSettings, type NotificationConfig } from "@/components/settings/notification-settings";
import { ThemeSettings } from "@/components/settings/theme-settings";
import { DataSettings, type DataConfig } from "@/components/settings/data-settings";
import { ConnectedAccounts, type ConnectedAccountsConfig } from "@/components/settings/connected-accounts";
import { SystemInfo } from "@/components/settings/system-info";
import { API_BASE } from "@/lib/api/client";

interface UserSettings {
  display_name: string;
  email: string;
  language: string;
  timezone: string;
  notifications: NotificationConfig;
  theme: string;
  accent_color: string;
  data: DataConfig;
  connected_accounts: ConnectedAccountsConfig;
  system: {
    version: string;
    api_status: "healthy" | "degraded" | "error";
    build_time: string;
    cache_size_mb: number;
  };
}

const DEFAULT_SETTINGS: UserSettings = {
  display_name: "Demo User",
  email: "demo@example.com",
  language: "ko",
  timezone: "Asia/Seoul",
  notifications: {
    email_alerts: true,
    push_alerts: false,
    price_threshold_pct: 5.0,
    daily_digest: true,
  },
  theme: "dark",
  accent_color: "violet",
  data: {
    refresh_interval_sec: 30,
    auto_refresh: true,
    auto_backup: false,
    cache_size_mb: 128,
  },
  connected_accounts: {
    google: false,
    apple: false,
    kakao: false,
    github: true,
  },
  system: {
    version: "0.3.1-sprint-08",
    api_status: "healthy",
    build_time: new Date().toISOString(),
    cache_size_mb: 42,
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: BE γ-sprint 완료 후 실 엔드포인트로 swap (현재 MSW stub 사용)
    fetch(`${API_BASE}/users/me/settings`)
      .then((res) => res.ok ? res.json() : Promise.reject(res.status))
      .then((data: UserSettings) => setSettings(data))
      .catch(() => {
        // MSW 없는 환경에서는 default 사용
      })
      .finally(() => setLoading(false));
  }, []);

  const patchSettings = useCallback(
    async (patch: Partial<UserSettings>) => {
      const optimistic = { ...settings, ...patch };
      setSettings(optimistic);

      try {
        // TODO: BE γ-sprint 완료 후 실 엔드포인트로 swap
        await fetch(`${API_BASE}/users/me/settings`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch),
        });
      } catch {
        // 실패 시 롤백
        setSettings(settings);
      }
    },
    [settings],
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">설정</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            개인 설정을 관리합니다. 테마, 알림, 데이터 옵션을 변경할 수 있습니다.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-64 animate-pulse rounded-xl border border-border bg-muted/20" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">설정</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          개인 설정을 관리합니다. 테마, 알림, 데이터 옵션을 변경할 수 있습니다.
        </p>
      </div>

      {/* 6 섹션 2×3 그리드 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* 좌상: 기본 설정 */}
        <GeneralSettings
          displayName={settings.display_name}
          email={settings.email}
          language={settings.language}
          timezone={settings.timezone}
        />

        {/* 중상: 알림 설정 */}
        <NotificationSettings
          config={settings.notifications}
          onChange={(notifications) => patchSettings({ notifications })}
        />

        {/* 우상: 테마 설정 */}
        <ThemeSettings
          accentColor={settings.accent_color}
          onAccentChange={(accent_color) => patchSettings({ accent_color })}
        />

        {/* 좌하: 데이터 설정 */}
        <DataSettings
          config={settings.data}
          onChange={(data) => patchSettings({ data })}
        />

        {/* 중하: 연결된 계정 */}
        <ConnectedAccounts config={settings.connected_accounts} />

        {/* 우하: 시스템 정보 */}
        <SystemInfo
          version={settings.system.version}
          apiStatus={settings.system.api_status}
          buildTime={settings.system.build_time}
          cacheSizeMb={settings.system.cache_size_mb}
        />
      </div>
    </div>
  );
}
