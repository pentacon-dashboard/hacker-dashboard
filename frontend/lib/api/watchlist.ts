import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";

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
