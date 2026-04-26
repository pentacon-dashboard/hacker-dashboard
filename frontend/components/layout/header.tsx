"use client";

import { useEffect, useState } from "react";
import { useTheme } from "@/hooks/use-theme";
import { Button } from "@/components/ui/button";
import { getHealth } from "@/lib/api/health";
import { useUiStore } from "@/stores/ui";
import { DateRangePicker } from "@/components/layout/date-range-picker";
import { NotificationBell } from "@/components/layout/notification-bell";
import { CsvUploadButton } from "@/components/layout/csv-upload-button";
import { Suspense } from "react";
import { useLocale } from "@/lib/i18n/locale-provider";

type HealthStatus = "ok" | "error" | "pending";

const ENV = process.env["NEXT_PUBLIC_ENV"] ?? "dev";

function useHealthPolling(intervalMs = 10000): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>("pending");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        await getHealth();
        if (!cancelled) setStatus("ok");
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    void check();
    const id = setInterval(() => void check(), intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return status;
}

export function Header() {
  const { theme, setTheme, isDark, mounted } = useTheme();
  const healthStatus = useHealthPolling(10000);
  const toggleMobileMenu = useUiStore((s) => s.toggleMobileMenu);
  const { t } = useLocale();

  function handleToggle() {
    setTheme(isDark ? "light" : "dark");
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/50 bg-background px-4">
      {/* 좌측: 모바일 햄버거 버튼만 (페이지 제목 제거 — 목업은 본문 H1) */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleMobileMenu}
          className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          aria-label="메뉴 열기"
          type="button"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="4" x2="20" y1="6" y2="6" />
            <line x1="4" x2="20" y1="12" y2="12" />
            <line x1="4" x2="20" y1="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* 우측: DateRangePicker → NotificationBell → health dot → ENV 배지 → theme toggle → CsvUploadButton */}
      <div className="ml-auto flex items-center gap-2">
        {/* DateRangePicker — useSearchParams() 사용하므로 Suspense 경계 필요 */}
        <Suspense fallback={<div className="h-8 w-32 animate-pulse rounded-lg bg-muted" />}>
          <DateRangePicker />
        </Suspense>

        {/* 알림 벨 */}
        <NotificationBell />

        {/* API Health dot */}
        <div
          className="flex items-center gap-1.5"
          aria-label={`${t("header.apiOk")}: ${healthStatus === "ok" ? t("settings.system.healthy") : healthStatus === "error" ? t("settings.system.error") : t("common.loading")}`}
          title={`${t("header.apiOk")} ${healthStatus === "ok" ? t("settings.system.healthy") : healthStatus === "error" ? t("settings.system.error") : t("common.loading")}`}
        >
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              healthStatus === "ok"
                ? "bg-green-500"
                : healthStatus === "error"
                  ? "bg-red-500"
                  : "bg-yellow-400 animate-pulse"
            }`}
            aria-hidden="true"
          />
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {healthStatus === "ok" ? t("header.apiOk") : healthStatus === "error" ? `${t("header.apiOk")} ${t("common.error")}` : t("common.loading")}
          </span>
        </div>

        {/* 환경 배지 */}
        <span
          className={`rounded-lg px-1.5 py-0.5 text-xs font-semibold ${
            ENV === "prod"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground"
          }`}
          aria-label={`환경: ${ENV}`}
        >
          {ENV.toUpperCase()}
        </span>

        {/* 다크모드 토글 */}
        <Button
          variant="ghost"
          size="icon"
          onClick={handleToggle}
          aria-label={isDark ? t("header.lightMode") : t("header.darkMode")}
          data-testid="theme-toggle"
          suppressHydrationWarning
          className="h-8 w-8"
        >
          {mounted && isDark ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2" />
              <path d="M12 20v2" />
              <path d="m4.93 4.93 1.41 1.41" />
              <path d="m17.66 17.66 1.41 1.41" />
              <path d="M2 12h2" />
              <path d="M20 12h2" />
              <path d="m6.34 17.66-1.41 1.41" />
              <path d="m19.07 4.93-1.41 1.41" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
            </svg>
          )}
        </Button>

        <span className="sr-only" suppressHydrationWarning>
          {mounted ? `현재 테마: ${theme}` : "현재 테마"}
        </span>

        {/* CSV 업로드 버튼 */}
        <CsvUploadButton />
      </div>
    </header>
  );
}
