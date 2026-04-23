import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";

export type Citation = components["schemas"]["Citation"];

type SearchNewsResponse =
  paths["/search/news"]["get"]["responses"]["200"]["content"]["application/json"];

export async function searchNews(params: {
  query: string;
  symbols?: string[];
  k?: number;
}): Promise<SearchNewsResponse> {
  const qs = new URLSearchParams();
  qs.set("query", params.query);
  if (params.symbols && params.symbols.length > 0) {
    qs.set("symbols", params.symbols.join(","));
  }
  if (params.k != null) qs.set("k", String(params.k));
  return apiFetch<SearchNewsResponse>(`/search/news?${qs.toString()}`);
}
