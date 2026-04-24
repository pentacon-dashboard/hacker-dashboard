"use client";

import { useCallback, useEffect, useState } from "react";
import { GeneralSettings } from "@/components/settings/general-settings";
import { NotificationSettings, type NotificationConfig } from "@/components/settings/notification-settings";
import { ThemeSettings } from "@/components/settings/theme-settings";
import { DataSettings, type DataConfig } from "@/components/settings/data-settings";
import { ConnectedAccounts, type ConnectedAccountsConfig } from "@/components/settings/connected-accounts";
import { SystemInfo } from "@/components/settings/system-info";
import { API_BASE } from "@/lib/api/client";
import { useTheme, type Accent } from "@/hooks/use-theme";

// BE /users/me/settings 실제 스키마 — system 필드 없음
interface UserSettings {
  display_name?: string;
  name?: string;
  email: string;
  language: string;
  timezone: string;
  notifications: NotificationConfig;
  // BE 저장 경로: theme.mode / theme.accent (nested object)
  theme: { mode: string; accent: string };
  data: DataConfig;
  connected_accounts: ConnectedAccountsConfig | Array<{ provider: string; email: string; connected_at: string }>;
}

// 시스템 메타 — BE 미보유 필드, 클라이언트 상수로 관리
const SYSTEM_INFO = {
  version: process.env.NEXT_PUBLIC_APP_VERSION ?? "0.3.1-sprint-08",
  api_status: "healthy" as const,
  build_time: process.env.NEXT_PUBLIC_BUILD_TIME ?? new Date().toISOString(),
  cache_size_mb: 256,
};

function resolveDisplayName(s: UserSettings): string {
  return s.display_name ?? s.name ?? "Demo User";
}

function resolveAccentColor(s: UserSettings): Accent {
  const v = s.theme.accent ?? "violet";
  return isValidAccent(v) ? v : "violet";
}

function resolveThemeMode(s: UserSettings): string {
  return s.theme.mode ?? "system";
}

function resolveConnectedAccounts(s: UserSettings): ConnectedAccountsConfig {
  if (Array.isArray(s.connected_accounts)) {
    const providers = s.connected_accounts.map((a) => a.provider);
    return {
      google: providers.includes("google"),
      apple: providers.includes("apple"),
      kakao: providers.includes("kakao"),
      github: providers.includes("github"),
    };
  }
  return s.connected_accounts as ConnectedAccountsConfig;
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
  theme: { mode: "system", accent: "violet" },
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
};

function isValidAccent(v: string): v is Accent {
  return ["violet", "cyan", "blue", "orange", "rose"].includes(v);
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const { setAccent } = useTheme();

  useEffect(() => {
    // TODO: BE γ-sprint 완료 후 실 엔드포인트로 swap (현재 MSW stub 사용)
    fetch(`${API_BASE}/users/me/settings`)
      .then((res) => res.ok ? res.json() : Promise.reject(res.status))
      .then((data: UserSettings) => {
        setSettings(data);
        // BE 에 저장된 accent 를 전역 ThemeContext 와 동기화 (CSS 변수 즉시 반영)
        const beAccent = data.theme?.accent;
        if (beAccent && isValidAccent(beAccent)) {
          setAccent(beAccent);
        }
      })
      .catch(() => {
        // MSW 없는 환경에서는 default 사용
      })
      .finally(() => setLoading(false));
  }, [setAccent]);

  const patchSettings = useCallback(
    async (patch: Partial<UserSettings>) => {
      // theme 은 nested 병합 — 상위 spread 만으로는 덮어쓰기됨
      const mergedTheme: UserSettings["theme"] =
        patch.theme != null
          ? { ...settings.theme, ...patch.theme }
          : settings.theme;
      const optimistic: UserSettings = { ...settings, ...patch, theme: mergedTheme };
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
          displayName={resolveDisplayName(settings)}
          email={settings.email}
          language={settings.language}
          timezone={settings.timezone}
          onChange={(patch) => {
            const apiPatch: Partial<UserSettings> = {};
            if (patch.displayName !== undefined) {
              // BE 는 "name" 필드로 수신
              apiPatch.name = patch.displayName;
              apiPatch.display_name = patch.displayName;
            }
            if (patch.language !== undefined) apiPatch.language = patch.language;
            if (patch.timezone !== undefined) apiPatch.timezone = patch.timezone;
            void patchSettings(apiPatch);
          }}
        />

        {/* 중상: 알림 설정 */}
        <NotificationSettings
          config={settings.notifications}
          onChange={(notifications) => patchSettings({ notifications })}
        />

        {/* 우상: 테마 설정 */}
        <ThemeSettings
          accentColor={resolveAccentColor(settings)}
          onAccentChange={(accent) =>
            patchSettings({ theme: { mode: resolveThemeMode(settings), accent } })
          }
        />

        {/* 좌하: 데이터 설정 */}
        <DataSettings
          config={settings.data}
          onChange={(data) => patchSettings({ data })}
        />

        {/* 중하: 연결된 계정 */}
        <ConnectedAccounts config={resolveConnectedAccounts(settings)} />

        {/* 우하: 시스템 정보 — BE 미보유 필드, 클라이언트 상수 */}
        <SystemInfo
          version={SYSTEM_INFO.version}
          apiStatus={SYSTEM_INFO.api_status}
          buildTime={SYSTEM_INFO.build_time}
          cacheSizeMb={SYSTEM_INFO.cache_size_mb}
        />
      </div>
    </div>
  );
}
