"use client";

import { create } from "zustand";

export interface TickerData {
  market: string;
  symbol: string;
  price: number;
  change_pct: number;
  volume: number;
  ts: string;
}

interface TickersState {
  tickers: Record<string, TickerData>;
  upsert: (tick: TickerData) => void;
  getKey: (market: string, symbol: string) => string;
}

export function makeTickerKey(market: string, symbol: string): string {
  return `${market}:${symbol}`;
}

export const useTickersStore = create<TickersState>((set) => ({
  tickers: {},
  upsert: (tick) =>
    set((state) => ({
      tickers: {
        ...state.tickers,
        [makeTickerKey(tick.market, tick.symbol)]: tick,
      },
    })),
  getKey: makeTickerKey,
}));
