"use client";

import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface Trade {
  id: string;
  ticker: string;
  side: "buy" | "sell";
  price: string;
  quantity: string;
  timestamp: string;
}

const STUB_TRADES: Trade[] = [
  { id: "t1", ticker: "NVDA", side: "buy", price: "$510.20", quantity: "2", timestamp: "2026-04-22T09:30:00Z" },
  { id: "t2", ticker: "KRW-BTC", side: "sell", price: "₩73.2M", quantity: "0.01", timestamp: "2026-04-21T14:12:00Z" },
  { id: "t3", ticker: "005930.KS", side: "buy", price: "₩74,000", quantity: "10", timestamp: "2026-04-20T10:05:00Z" },
];

export function RecentTradesPanel() {
  return (
    <div className="space-y-3" data-testid="recent-trades-panel">
      <h3 className="text-xs font-semibold">최근 체결</h3>
      {STUB_TRADES.length === 0 ? (
        <p className="text-xs text-muted-foreground">최근 체결 내역 없음</p>
      ) : (
        <ul className="space-y-2" data-testid="recent-trades-list">
          {STUB_TRADES.map((trade) => {
            const isBuy = trade.side === "buy";
            const dateStr = new Date(trade.timestamp).toLocaleDateString("ko-KR", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
            return (
              <li
                key={trade.id}
                className="flex items-center justify-between gap-2 rounded-lg border p-2"
                data-testid={`trade-${trade.id}`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                      isBuy
                        ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400"
                        : "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400"
                    }`}
                    aria-hidden="true"
                  >
                    {isBuy ? (
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    ) : (
                      <ArrowDownRight className="h-3.5 w-3.5" />
                    )}
                  </span>
                  <div>
                    <p className="text-xs font-medium">{trade.ticker}</p>
                    <p className="text-[10px] text-muted-foreground">{dateStr}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-semibold tabular-nums">{trade.price}</p>
                  <p className="text-[10px] text-muted-foreground">x{trade.quantity}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-[10px] text-muted-foreground">* 데모 고정 샘플</p>
    </div>
  );
}
