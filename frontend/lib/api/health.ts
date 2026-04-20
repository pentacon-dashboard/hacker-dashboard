import type { paths } from "@shared/types/api";
import { apiFetch } from "./client";

type HealthResponse =
  paths["/health"]["get"]["responses"]["200"]["content"]["application/json"];

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
