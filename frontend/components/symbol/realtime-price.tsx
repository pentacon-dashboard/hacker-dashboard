"use client";

import { useTickersStore, makeTickerKey } from "@/stores/tickers";
import { useRealtimeTicker } from "@/lib/realtime/use-realtime-ticker";
import type { Quote } from "@/lib/api/symbols";

interface RealtimePriceProps {
  market: string;
  code: string;
  initialQuote: Quote;
}

export function RealtimePrice({
  market,
  code,
  initialQuote,
}: RealtimePriceProps) {
  useRealtimeTicker([{ market, code }]);

  const ticker = useTickersStore(
    (s) => s.tickers[makeTickerKey(market, code)],
  );

  const price = ticker?.price ?? initialQuote.price;
  const changePct = ticker?.change_pct ?? initialQuote.change_pct;
  const currency = initialQuote.currency;
  const isPositive = changePct >= 0;

  const formatted =
    currency === "KRW"
      ? new Intl.NumberFormat("ko-KR", {
          style: "currency",
          currency: "KRW",
          maximumFractionDigits: 0,
        }).format(price)
      : new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: currency || "USD",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(price);

  return (
    <div className="flex flex-wrap items-baseline gap-3">
      <span
        data-testid="symbol-price"
        className="text-3xl font-bold tabular-nums"
      >
        {formatted}
      </span>
      <span
        data-testid="change-pct"
        className={
          isPositive
            ? "flex items-center gap-1 text-lg font-medium text-green-600 dark:text-green-400"
            : "flex items-center gap-1 text-lg font-medium text-red-600 dark:text-red-400"
        }
      >
        {isPositive ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden="true"
          >
            <path d="m5 12 7-7 7 7" />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden="true"
          >
            <path d="m19 12-7 7-7-7" />
          </svg>
        )}
        {Math.abs(changePct).toFixed(2)}%
      </span>
    </div>
  );
}
