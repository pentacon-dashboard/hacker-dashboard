"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

// TODO: GET /market/status 연동 후 실제 서버 세션 상태로 교체
type MarketSession = "장중" | "장후" | "휴장";

function getMarketSession(now: Date): MarketSession {
  const hour = now.getHours();
  const minute = now.getMinutes();
  const totalMinutes = hour * 60 + minute;
  const day = now.getDay(); // 0=일, 6=토

  // 주말은 휴장
  if (day === 0 || day === 6) return "휴장";

  // 09:00 ~ 15:30 = 장중
  if (totalMinutes >= 9 * 60 && totalMinutes < 15 * 60 + 30) return "장중";

  // 15:30 이후 ~ 18:00 = 장후 (시간외 거래)
  if (totalMinutes >= 15 * 60 + 30 && totalMinutes < 18 * 60) return "장후";

  return "휴장";
}

const SESSION_STYLE: Record<MarketSession, string> = {
  장중: "bg-emerald-500/20 text-emerald-400",
  장후: "bg-amber-500/20 text-amber-400",
  휴장: "bg-muted text-muted-foreground",
};

interface MarketStatusCardProps {
  collapsed?: boolean;
}

/**
 * 사이드바 최하단 시장 상태 카드.
 * - 세션 배지(장중/장후/휴장), 현재 시각, 거래량 배지
 * - BE 연동 없이 클라이언트 시각 + 하드코드 세션 로직으로 우선 구현
 */
export function MarketStatusCard({ collapsed = false }: MarketStatusCardProps) {
  const [now, setNow] = useState<Date>(() => new Date());

  // 1분마다 현재 시각 갱신
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const session = getMarketSession(now);
  const timeStr = new Intl.DateTimeFormat("ko-KR", {
    hour: "numeric",
    minute: "numeric",
  }).format(now);

  if (collapsed) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-border/50 bg-card/50 p-1.5"
        aria-label={`시장 상태: ${session}`}
        title={`시장 상태: ${session} | ${timeStr}`}
      >
        <span
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            session === "장중"
              ? "bg-emerald-400 animate-pulse"
              : session === "장후"
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
      aria-label="시장 상태"
    >
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          시장 상태
        </span>
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-[9px] font-bold",
            SESSION_STYLE[session],
          )}
          aria-label={`세션: ${session}`}
        >
          {session}
        </span>
      </div>

      <p className="text-xs font-medium text-foreground" aria-live="polite">
        {timeStr}
      </p>

      {/* 거래량 — stub "거래량 좋음" */}
      <div className="mt-1 flex items-center gap-1">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
        <span className="text-[10px] text-muted-foreground">거래량 좋음</span>
      </div>
    </div>
  );
}
