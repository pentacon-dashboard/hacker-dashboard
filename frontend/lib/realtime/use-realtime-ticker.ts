"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { WS_BASE } from "@/lib/api/client";
import { getQuote } from "@/lib/api/symbols";
import { useTickersStore, type TickerData } from "@/stores/tickers";

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;
const REALTIME_WS_DISABLED =
  process.env["NEXT_PUBLIC_DISABLE_REALTIME_WS"] === "1";

interface SymbolSpec {
  market: string;
  code: string;
}

interface WsTickMessage {
  market: string;
  symbol: string;
  price: number;
  change_pct: number;
  volume: number;
  ts: string;
}

function isWsTickMessage(val: unknown): val is WsTickMessage {
  if (typeof val !== "object" || val === null) return false;
  const v = val as Record<string, unknown>;
  return (
    typeof v["market"] === "string" &&
    typeof v["symbol"] === "string" &&
    typeof v["price"] === "number" &&
    typeof v["change_pct"] === "number" &&
    typeof v["volume"] === "number" &&
    typeof v["ts"] === "string"
  );
}

/**
 * 심볼 배열을 받아 /ws/ticks WebSocket 에 연결하고 Zustand store 에 upsert 한다.
 * WS 연결 실패 시 최대 3회 exponential backoff 재시도.
 * 재시도 초과 시 TanStack Query polling fallback (5초 간격) 으로 전환.
 */
export function useRealtimeTicker(symbols: SymbolSpec[]) {
  const upsert = useTickersStore((s) => s.upsert);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const wsFailed = useRef(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [useFallback, setUseFallback] = useState(REALTIME_WS_DISABLED);

  // caller 가 매 렌더마다 새 배열을 넘겨도 useEffect 가 재실행되지 않도록
  // 내용 기반 primitive key 로 참조 안정화.
  const symbolsKey = symbols.map((s) => `${s.market}:${s.code}`).join(",");

  const { data: fallbackQuotes } = useQuery({
    queryKey: ["quote-fallback", symbolsKey],
    queryFn: () =>
      Promise.all(
        symbols.map(({ market, code }) =>
          getQuote(market, code).catch(() => null),
        ),
      ),
    refetchInterval: 5000,
    enabled: useFallback && Boolean(symbolsKey),
  });

  // fallback 데이터를 store 에 반영
  useEffect(() => {
    if (!useFallback || !fallbackQuotes) return;
    for (const quote of fallbackQuotes) {
      if (
        quote?.price == null ||
        !quote.symbol ||
        !quote.market ||
        !quote.timestamp
      ) {
        continue;
      }
      const tick: TickerData = {
        market: quote.market,
        symbol: quote.symbol,
        price: quote.price,
        change_pct: quote.change_pct ?? 0,
        volume: quote.volume ?? 0,
        ts: quote.timestamp,
      };
      upsert(tick);
    }
  }, [fallbackQuotes, upsert, useFallback]);

  const connect = useCallback(() => {
    if (!symbolsKey) return;
    if (REALTIME_WS_DISABLED) return;

    const url = `${WS_BASE}/ws/ticks?markets=${encodeURIComponent(symbolsKey)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const parsed: unknown = JSON.parse(event.data);
        if (isWsTickMessage(parsed)) {
          upsert(parsed);
        }
      } catch {
        // 파싱 실패 무시
      }
    };

    ws.onopen = () => {
      retriesRef.current = 0;
    };

    ws.onerror = () => {
      // onclose 에서 재시도 처리
    };

    ws.onclose = () => {
      if (retriesRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        timeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        wsFailed.current = true;
        setUseFallback(true);
      }
    };
  }, [symbolsKey, upsert]);

  useEffect(() => {
    connect();

    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
      if (wsRef.current) {
        // cleanup 시 재연결 방지: onclose 를 noop 으로 교체
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
    // symbols 배열이 변경될 때마다 재연결
  }, [connect]);
}
