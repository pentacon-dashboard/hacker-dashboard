"use client";

export type PercentValue = number | string | null | undefined;

export function parsePercent(value: PercentValue): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }

  const normalized = String(value ?? "")
    .replace(/,/g, "")
    .replace(/%/g, "")
    .trim();
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function isNonNegativePercent(value: PercentValue): boolean {
  return parsePercent(value) >= 0;
}

export function formatSignedPercent(value: PercentValue, decimals = 2): string {
  const parsed = parsePercent(value);
  const prefix = parsed > 0 ? "+" : "";
  return `${prefix}${parsed.toFixed(decimals)}%`;
}
