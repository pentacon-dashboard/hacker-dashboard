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
  top_gainer_name: string;
  top_gainer_pct: string;
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

// --- Phase 2: /watchlist/alerts CRUD ---

/** BE /watchlist/alerts GET 응답 */
export interface WatchlistAlert {
  id: number;
  user_id: string;
  symbol: string;
  market: string;
  direction: "above" | "below";
  threshold: string;
  enabled: boolean;
  created_at: string;
}

/** POST /watchlist/alerts body */
export interface AlertCreate {
  symbol: string;
  market: string;
  direction: "above" | "below";
  threshold: number;
}

/** PATCH /watchlist/alerts/{id} body */
export interface AlertUpdate {
  enabled?: boolean;
  threshold?: number;
}

export async function getAlerts(): Promise<WatchlistAlert[]> {
  return apiFetch<WatchlistAlert[]>("/watchlist/alerts");
}

export async function createAlert(
  body: AlertCreate,
): Promise<WatchlistAlert> {
  return apiFetch<WatchlistAlert>("/watchlist/alerts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAlert(
  id: number,
  patch: AlertUpdate,
): Promise<WatchlistAlert> {
  return apiFetch<WatchlistAlert>(`/watchlist/alerts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteAlert(id: number): Promise<void> {
  await apiFetch<void>(`/watchlist/alerts/${id}`, {
    method: "DELETE",
  });
}
