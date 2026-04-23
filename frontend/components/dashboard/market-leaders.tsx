"use client";

import Image from "next/image";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getMarketLeaders,
  type MarketLeaderResponse,
} from "@/lib/api/portfolio";

/** 하위 호환: page.tsx 가 직접 leaders 를 내려주던 시절 인터페이스 유지 */
export interface MarketLeader {
  rank: number;
  name: string;
  ticker: string;
  logo_url: string | null;
  /** BE: price_display(null 가능) 또는 수동 포맷 문자열 */
  price_display: string | null;
  change_pct: string;
  change_krw: string | null;
}

interface MarketLeadersProps {
  /** props 로 직접 주입할 때만 사용 (단위 테스트 등). 없으면 내부 useQuery 호출. */
  leaders?: MarketLeader[];
  limit?: number;
}

const PASTEL_BG: string[] = [
  "bg-violet-500/10 dark:bg-violet-500/15",
  "bg-blue-500/10 dark:bg-blue-500/15",
  "bg-emerald-500/10 dark:bg-emerald-500/15",
  "bg-amber-500/10 dark:bg-amber-500/15",
  "bg-rose-500/10 dark:bg-rose-500/15",
];

function TickerAvatar({
  name,
  logoUrl,
}: {
  name: string;
  logoUrl: string | null;
}) {
  if (logoUrl) {
    return (
      <div className="relative h-9 w-9 shrink-0 overflow-hidden rounded-full">
        <Image
          src={logoUrl}
          alt={name}
          fill
          sizes="36px"
          className="object-cover"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
      </div>
    );
  }
  const initials = name
    .split(/\s+/)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .slice(0, 2)
    .join("");
  return (
    <div
      aria-hidden="true"
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground"
    >
      {initials}
    </div>
  );
}

function LeaderList({ leaders }: { leaders: MarketLeader[] }) {
  if (leaders.length === 0) {
    return (
      <div
        className="flex h-40 items-center justify-center text-sm text-muted-foreground"
        data-testid="market-leaders-empty"
      >
        시장 주도주 데이터 없음
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2" data-testid="market-leaders">
      {leaders.map((leader, idx) => {
        const changeNum = Number(leader.change_pct);
        const isPositive = changeNum >= 0;
        const bgClass = PASTEL_BG[idx % PASTEL_BG.length] ?? PASTEL_BG[0]!;

        return (
          <li
            key={leader.ticker}
            className={`flex items-center gap-3 rounded-xl p-3 ${bgClass}`}
            data-testid={`market-leader-${leader.rank}`}
          >
            <TickerAvatar name={leader.name} logoUrl={leader.logo_url} />

            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold">{leader.name}</p>
              <p className="text-[10px] text-muted-foreground">{leader.ticker}</p>
            </div>

            <div className="shrink-0 text-right">
              <p className="text-xs font-semibold tabular-nums">
                {leader.price_display ?? "-"}
              </p>
              <p
                className={`flex items-center justify-end gap-0.5 text-[10px] font-semibold tabular-nums ${
                  isPositive
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {isPositive ? (
                  <TrendingUp className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3" aria-hidden="true" />
                )}
                {isPositive ? "+" : ""}
                {changeNum.toFixed(2)}%
              </p>
              {leader.change_krw && (
                <p className="text-[10px] text-muted-foreground">
                  {leader.change_krw}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** BE 응답을 표시용 MarketLeader 로 변환 */
function toDisplayLeader(r: MarketLeaderResponse): MarketLeader {
  return {
    rank: r.rank,
    name: r.name,
    ticker: r.ticker,
    logo_url: r.logo_url,
    price_display: r.price_display ?? `${r.currency} ${r.price}`,
    change_pct: r.change_pct,
    change_krw: r.change_krw,
  };
}

export function MarketLeaders({ leaders, limit = 5 }: MarketLeadersProps) {
  const shouldFetch = leaders === undefined;

  const query = useQuery({
    queryKey: ["portfolio", "market-leaders", limit],
    queryFn: () => getMarketLeaders(limit),
    staleTime: 60_000,
    enabled: shouldFetch,
  });

  // props 로 직접 주입된 경우 (단위 테스트 / page.tsx fallback)
  if (!shouldFetch) {
    return <LeaderList leaders={leaders} />;
  }

  if (query.isLoading) {
    return (
      <div className="space-y-2" data-testid="market-leaders-loading">
        {Array.from({ length: limit }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (query.isError) {
    return (
      <div
        role="alert"
        className="rounded-md border border-destructive bg-destructive/10 p-3 text-xs text-destructive"
        data-testid="market-leaders-error"
      >
        시장 주도주 로드 실패
      </div>
    );
  }

  const displayLeaders = (query.data ?? []).map(toDisplayLeader);

  return <LeaderList leaders={displayLeaders} />;
}
