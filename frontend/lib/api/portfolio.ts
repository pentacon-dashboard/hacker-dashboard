import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";
import type { SectorHeatmapTile } from "@/components/portfolio/sector-heatmap";
import type { MonthlyReturnCell } from "@/components/portfolio/monthly-return-calendar";
import type { AiInsightResponse } from "@/components/portfolio/ai-insight-card";

// --- 타입 재내보내기 (수동 선언 금지 — 생성 타입만 사용) ---
export type HoldingResponse = components["schemas"]["HoldingResponse"];
export type HoldingCreate = components["schemas"]["HoldingCreate"];
export type HoldingUpdate = components["schemas"]["HoldingUpdate"];
export type HoldingDetail = components["schemas"]["HoldingDetail"];
export type PortfolioSummary = components["schemas"]["PortfolioSummary"];
export type SnapshotResponse = components["schemas"]["SnapshotResponse"];
export type PortfolioClientsResponse = components["schemas"]["PortfolioClientsResponse"];
export type ClientBriefingReportRequest =
  components["schemas"]["ClientBriefingReportRequest"];
export type ClientBriefingReportResponse =
  components["schemas"]["ClientBriefingReportResponse"];

type ListHoldingsResponse =
  paths["/portfolio/holdings"]["get"]["responses"]["200"]["content"]["application/json"];

type CreateHoldingResponse =
  paths["/portfolio/holdings"]["post"]["responses"]["201"]["content"]["application/json"];

type UpdateHoldingResponse =
  paths["/portfolio/holdings/{holding_id}"]["patch"]["responses"]["200"]["content"]["application/json"];

type GetSummaryResponse =
  paths["/portfolio/summary"]["get"]["responses"]["200"]["content"]["application/json"];

type ListSnapshotsResponse =
  paths["/portfolio/snapshots"]["get"]["responses"]["200"]["content"]["application/json"];

// --- API 래퍼 ---

export async function listHoldings(): Promise<ListHoldingsResponse> {
  return apiFetch<ListHoldingsResponse>("/portfolio/holdings");
}

export async function listHoldingsByClient(
  clientId?: string,
): Promise<ListHoldingsResponse> {
  const qs = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  return apiFetch<ListHoldingsResponse>(`/portfolio/holdings${qs}`);
}

export async function createHolding(
  body: HoldingCreate,
): Promise<CreateHoldingResponse> {
  return apiFetch<CreateHoldingResponse>("/portfolio/holdings", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateHolding(
  id: number,
  patch: HoldingUpdate,
): Promise<UpdateHoldingResponse> {
  return apiFetch<UpdateHoldingResponse>(`/portfolio/holdings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteHolding(id: number): Promise<void> {
  await apiFetch<void>(`/portfolio/holdings/${id}`, {
    method: "DELETE",
  });
}

export async function getPortfolioSummary(
  periodDays?: number,
  clientId?: string,
): Promise<GetSummaryResponse> {
  const params = new URLSearchParams();
  if (periodDays != null) params.set("period_days", String(periodDays));
  if (clientId) params.set("client_id", clientId);
  const qs = params.toString();
  return apiFetch<GetSummaryResponse>(`/portfolio/summary${qs ? `?${qs}` : ""}`);
}

export async function getSnapshots(
  from?: string,
  to?: string,
  clientId?: string,
): Promise<ListSnapshotsResponse> {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  if (clientId) params.set("client_id", clientId);
  const qs = params.toString();
  return apiFetch<ListSnapshotsResponse>(
    `/portfolio/snapshots${qs ? `?${qs}` : ""}`,
  );
}

export async function getPortfolioClients(): Promise<PortfolioClientsResponse> {
  return apiFetch<PortfolioClientsResponse>("/portfolio/clients");
}

// --- Sprint-08 B-α 신규 엔드포인트 (BE 미구현 시 MSW fallback) ---

export async function getSectorHeatmap(clientId?: string): Promise<SectorHeatmapTile[]> {
  const qs = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  return apiFetch<SectorHeatmapTile[]>(`/portfolio/sectors/heatmap${qs}`);
}

export async function getMonthlyReturns(
  year?: number,
  clientId?: string,
): Promise<MonthlyReturnCell[]> {
  const params = new URLSearchParams();
  if (year != null) params.set("year", String(year));
  if (clientId) params.set("client_id", clientId);
  const qs = params.toString();
  return apiFetch<MonthlyReturnCell[]>(`/portfolio/monthly-returns${qs ? `?${qs}` : ""}`);
}

export async function getAiInsight(clientId?: string): Promise<AiInsightResponse> {
  const qs = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  return apiFetch<AiInsightResponse>(`/portfolio/ai-insight${qs}`);
}

export async function createClientBriefingReport(
  body: ClientBriefingReportRequest,
): Promise<ClientBriefingReportResponse> {
  return apiFetch<ClientBriefingReportResponse>("/portfolio/reports/client-briefing", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// --- Phase 2: /portfolio/market-leaders ---

/** BE /portfolio/market-leaders 응답 형태 */
export interface MarketLeaderResponse {
  rank: number;
  ticker: string;
  name: string;
  market: string;
  price: string;
  change_pct: string;
  currency: string;
  logo_url: string | null;
  price_display: string | null;
  change_krw: string | null;
}

export async function getMarketLeaders(
  limit = 5,
): Promise<MarketLeaderResponse[]> {
  return apiFetch<MarketLeaderResponse[]>(
    `/portfolio/market-leaders?limit=${limit}`,
  );
}
