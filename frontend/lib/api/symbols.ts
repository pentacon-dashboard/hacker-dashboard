import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";

export type SymbolInfo = components["schemas"]["SymbolInfo"];
export type Quote = components["schemas"]["Quote"];
export type OhlcBar = components["schemas"]["OhlcBar"];

type SearchSymbolsResponse =
  paths["/market/symbols/search"]["get"]["responses"]["200"]["content"]["application/json"];

type GetMarketQuoteResponse =
  paths["/market/quotes/{market}/{code}"]["get"]["responses"]["200"]["content"]["application/json"];

type GetOhlcResponse =
  paths["/market/ohlc/{market}/{code}"]["get"]["responses"]["200"]["content"]["application/json"];

export async function searchSymbols(q: string): Promise<SearchSymbolsResponse> {
  return apiFetch<SearchSymbolsResponse>(
    `/market/symbols/search?q=${encodeURIComponent(q)}`,
  );
}

export async function getQuote(
  market: string,
  code: string,
): Promise<GetMarketQuoteResponse> {
  return apiFetch<GetMarketQuoteResponse>(
    `/market/quotes/${encodeURIComponent(market)}/${encodeURIComponent(code)}`,
  );
}

export async function getOhlc(
  market: string,
  code: string,
  interval: "1d" | "1m" = "1d",
  limit = 100,
): Promise<GetOhlcResponse> {
  const params = new URLSearchParams({
    interval,
    limit: String(limit),
  });
  return apiFetch<GetOhlcResponse>(
    `/market/ohlc/${encodeURIComponent(market)}/${encodeURIComponent(code)}?${params.toString()}`,
  );
}
