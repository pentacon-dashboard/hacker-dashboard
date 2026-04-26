"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

type MarketSession = "open" | "afterHours" | "closed";

function getMarketSession(now: Date): MarketSession {
  const hour = now.getHours();
  const minute = now.getMinutes();
  const totalMinutes = hour * 60 + minute;
  const day = now.getDay(); // 0=일, 6=토

  if (day === 0 || day === 6) return "closed";
  if (totalMinutes >= 9 * 60 && totalMinutes < 15 * 60 + 30) return "open";
  if (totalMinutes >= 15 * 60 + 30 && totalMinutes < 18 * 60) return "afterHours";
  return "closed";
}

const SESSION_STYLE: Record<MarketSession, string> = {
  open: "bg-emerald-500/20 text-emerald-400",
  afterHours: "bg-amber-500/20 text-amber-400",
  closed: "bg-muted text-muted-foreground",
};

const SESSION_KEY: Record<MarketSession, string> = {
  open: "sidebar.marketSession.open",
  afterHours: "sidebar.marketSession.afterHours",
  closed: "sidebar.marketSession.closed",
};

interface MarketStatusCardProps {
  collapsed?: boolean;
}

/**
 * 사이드바 최하단 시장 상태 카드.
 */
export function MarketStatusCard({ collapsed = false }: MarketStatusCardProps) {
  const { locale, t } = useLocale();
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const session: MarketSession = now ? getMarketSession(now) : "closed";
  const sessionLabel = t(SESSION_KEY[session]);
  const fmtLocale = locale === "en" ? "en-US" : "ko-KR";
  const timeStr = now
    ? new Intl.DateTimeFormat(fmtLocale, { hour: "numeric", minute: "numeric", hour12: locale === "en" })
        .format(now)
    : "--:--";

  if (collapsed) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-border/50 bg-card/50 p-1.5"
        aria-label={`${t("sidebar.marketStatus")}: ${sessionLabel}`}
        title={`${t("sidebar.marketStatus")}: ${sessionLabel} | ${timeStr}`}
      >
        <span
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            session === "open"
              ? "bg-emerald-400 animate-pulse"
              : session === "afterHours"
                ? "bg-amber-400"
                : "bg-muted-foreground",
          )}
          aria-hidden="true"
        />
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-border/50 bg-card/50 px-2.5 py-2"
      aria-label={t("sidebar.marketStatus")}
    >
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          {t("sidebar.marketStatus")}
        </span>
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-[9px] font-bold",
            SESSION_STYLE[session],
          )}
          aria-label={`${t("sidebar.session")}: ${sessionLabel}`}
        >
          {sessionLabel}
        </span>
      </div>

      <p className="text-xs font-medium text-foreground" aria-live="polite">
        {timeStr}
      </p>

      <div className="mt-1 flex items-center gap-1">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
        <span className="text-[10px] text-muted-foreground">{t("sidebar.volumeGood")}</span>
      </div>
    </div>
  );
}
