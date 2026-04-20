import type { components, paths } from "@shared/types/api";
import { apiFetch } from "./client";

// --- 타입 재내보내기 (수동 선언 금지 — 생성 타입만 사용) ---
export type HoldingResponse = components["schemas"]["HoldingResponse"];
export type HoldingCreate = components["schemas"]["HoldingCreate"];
export type HoldingUpdate = components["schemas"]["HoldingUpdate"];
export type HoldingDetail = components["schemas"]["HoldingDetail"];
export type PortfolioSummary = components["schemas"]["PortfolioSummary"];
export type SnapshotResponse = components["schemas"]["SnapshotResponse"];

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

export async function getPortfolioSummary(): Promise<GetSummaryResponse> {
  return apiFetch<GetSummaryResponse>("/portfolio/summary");
}

export async function getSnapshots(
  from?: string,
  to?: string,
): Promise<ListSnapshotsResponse> {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const qs = params.toString();
  return apiFetch<ListSnapshotsResponse>(
    `/portfolio/snapshots${qs ? `?${qs}` : ""}`,
  );
}
