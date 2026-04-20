"use client";

import type { components } from "@shared/types/api";
import { ApiError } from "./client";

export type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];
export type AnalyzeMeta = components["schemas"]["AnalyzeMeta"];
export type CacheMetrics = components["schemas"]["CacheMetrics"];

const API_BASE =
  typeof window !== "undefined"
    ? (process.env["NEXT_PUBLIC_API_BASE"] ?? "http://localhost:8000")
    : (process.env["NEXT_PUBLIC_API_BASE"] ?? "http://localhost:8000");

export async function analyzeCsv(
  file: File,
  opts?: { userNote?: string; symbolHint?: string },
): Promise<{ response: AnalyzeResponse; cacheHeader: string | null }> {
  const formData = new FormData();
  formData.append("file", file);
  if (opts?.userNote) formData.append("user_note", opts.userNote);
  if (opts?.symbolHint) formData.append("symbol_hint", opts.symbolHint);

  const res = await fetch(`${API_BASE}/analyze/csv`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new ApiError(res.status, `CSV 분석 오류 ${res.status}`);
  }

  const cacheHeader = res.headers.get("X-Cache");
  const response = (await res.json()) as AnalyzeResponse;
  return { response, cacheHeader };
}

/**
 * 심볼만 주면 BE 가 시장 어댑터로 OHLC 90일을 자동 프리페치해서 분석한다.
 * CSV 파일 불필요 — 실제 시세 기반.
 * include_portfolio_context: true 시 BE가 DB holdings를 조회해 개인화 분석 수행.
 */
export async function analyzeBySymbol(
  market: string,
  code: string,
  opts?: { includePortfolioContext?: boolean },
): Promise<{ response: AnalyzeResponse; cacheHeader: string | null }> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data: [],
      symbol: { market, code },
      include_portfolio_context: opts?.includePortfolioContext ?? false,
    }),
  });

  if (!res.ok) {
    throw new ApiError(res.status, `심볼 분석 오류 ${res.status}`);
  }

  const cacheHeader = res.headers.get("X-Cache");
  const response = (await res.json()) as AnalyzeResponse;
  return { response, cacheHeader };
}
