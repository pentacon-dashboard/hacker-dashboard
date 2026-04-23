import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";
import type { TopListItem } from "@/components/watchlist/popular-top5";

export type WatchlistItemResponse =
  components["schemas"]["WatchlistItemResponse"];
export type WatchlistItemCreate = components["schemas"]["WatchlistItemCreate"];

type ListWatchlistResponse =
  paths["/market/watchlist/items"]["get"]["responses"]["200"]["content"]["application/json"];

type AddWatchlistResponse =
  paths["/market/watchlist/items"]["post"]["responses"]["201"]["content"]["application/json"];

export async function listWatchlist(): Promise<ListWatchlistResponse> {
  return apiFetch<ListWatchlistResponse>("/market/watchlist/items");
}

export async function addWatchlist(
  body: WatchlistItemCreate,
): Promise<AddWatchlistResponse> {
  return apiFetch<AddWatchlistResponse>("/market/watchlist/items", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function removeWatchlist(id: number): Promise<void> {
  await apiFetch<void>(`/market/watchlist/items/${id}`, {
    method: "DELETE",
  });
}

// --- Sprint-08 B-β 신규 엔드포인트 (MSW fallback) ---

export interface WatchlistSummary {
  watched_count: number;
  up_avg_pct: string;
  down_avg_pct: string;
  top_gainer: string;
}

export async function getWatchlistSummary(): Promise<WatchlistSummary> {
  return apiFetch<WatchlistSummary>("/watchlist/summary");
}

export async function getWatchlistPopular(): Promise<TopListItem[]> {
  return apiFetch<TopListItem[]>("/watchlist/popular");
}

export interface GainersLosersResponse {
  gainers: TopListItem[];
  losers: TopListItem[];
}

export async function getWatchlistGainersLosers(): Promise<GainersLosersResponse> {
  return apiFetch<GainersLosersResponse>("/watchlist/gainers-losers");
}
