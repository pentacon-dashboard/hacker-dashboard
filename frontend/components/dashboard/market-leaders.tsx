"use client";

import Image from "next/image";
import { TrendingUp, TrendingDown } from "lucide-react";

export interface MarketLeader {
  rank: number;
  name: string;
  ticker: string;
  logo_url: string | null;
  price_display: string;
  change_pct: string;
  change_krw: string | null;
}

interface MarketLeadersProps {
  leaders: MarketLeader[];
}

const PASTEL_BG: string[] = [
  "bg-violet-500/10 dark:bg-violet-500/15",
  "bg-blue-500/10 dark:bg-blue-500/15",
  "bg-emerald-500/10 dark:bg-emerald-500/15",
];

function TickerAvatar({ name, logoUrl }: { name: string; logoUrl: string | null }) {
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

export function MarketLeaders({ leaders }: MarketLeadersProps) {
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
              <p className="text-xs font-semibold tabular-nums">{leader.price_display}</p>
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
                <p className="text-[10px] text-muted-foreground">{leader.change_krw}</p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
