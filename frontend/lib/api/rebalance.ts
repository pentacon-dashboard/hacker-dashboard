import type { components } from "@shared/types/api";
import { apiFetch } from "./client";

// --- 타입 재내보내기 (수동 선언 금지 — 생성 타입만 사용) ---
export type RebalanceRequest = components["schemas"]["RebalanceRequest"];
export type RebalanceResponse = components["schemas"]["RebalanceResponse"];
export type RebalanceAction = components["schemas"]["RebalanceAction"];
export type TargetAllocation = components["schemas"]["TargetAllocation"];
export type RebalanceConstraints = components["schemas"]["RebalanceConstraints"];
export type RebalanceSummary = components["schemas"]["RebalanceSummary"];
export type RebalanceMeta = components["schemas"]["RebalanceMeta"];
export type LLMAnalysis = components["schemas"]["LLMAnalysis"];

// --- API 래퍼 ---

export async function requestRebalance(
  req: RebalanceRequest,
): Promise<RebalanceResponse> {
  return apiFetch<RebalanceResponse>("/portfolio/rebalance", {
    method: "POST",
    body: JSON.stringify(req),
  });
}
