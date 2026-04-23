"use client";

import { useEffect, useState } from "react";

const DATA_SOURCES = "FinHub, IEX, Alpha Vantage, Bloomberg, Reuters";

function getTimeString(date: Date): string {
  return new Intl.DateTimeFormat("ko-KR", {
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
 * - 좌측: 데이터 출처 표기
 * - 우측: "실시간 지연 약 20분 · 업데이트: {현재 시각 ko-KR}" — 1분마다 갱신
 */
export function AppFooter() {
  const [updateTime, setUpdateTime] = useState<string>(() =>
    getTimeString(new Date()),
  );

  // 1분마다 업데이트 시각 갱신
  useEffect(() => {
    const id = setInterval(() => {
      setUpdateTime(getTimeString(new Date()));
    }, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <footer
      className="flex shrink-0 items-center justify-between border-t border-border/50 bg-background px-6 py-2.5"
      aria-label="풋터 정보"
      data-testid="app-footer"
    >
      <p className="text-[10px] text-muted-foreground">
        <span className="font-medium">데모용</span>
        {" • "}
        가격 데이터: {DATA_SOURCES}
      </p>
      <p className="text-[10px] text-muted-foreground" aria-live="polite">
        실시간 지연 약 20분 · 업데이트: {updateTime}
      </p>
    </footer>
  );
}
