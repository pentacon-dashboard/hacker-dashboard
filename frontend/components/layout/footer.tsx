"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/lib/i18n/locale-provider";

const DATA_SOURCES = "FinHub, IEX, Alpha Vantage, Bloomberg, Reuters";

function getTimeString(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale === "en" ? "en-US" : "ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

/**
 * AppFooter — 전 페이지 공통 하단 풋터.
 */
export function AppFooter() {
  const [updateTime, setUpdateTime] = useState<string>("—");
  const { locale, t } = useLocale();

  useEffect(() => {
    setUpdateTime(getTimeString(new Date(), locale));
    const id = setInterval(() => {
      setUpdateTime(getTimeString(new Date(), locale));
    }, 60_000);
    return () => clearInterval(id);
  }, [locale]);

  return (
    <footer
      className="flex shrink-0 items-center justify-between border-t border-border/50 bg-background px-6 py-2.5"
      aria-label="footer"
      data-testid="app-footer"
    >
      <p className="text-[10px] text-muted-foreground">
        {t("footer.dataProviders").replace(
          "FinHub, IEX, Alpha Vantage, Bloomberg, Reuters",
          DATA_SOURCES,
        )}
      </p>
      <p className="text-[10px] text-muted-foreground" aria-live="polite">
        {t("footer.delay", { time: updateTime })}
      </p>
    </footer>
  );
}
