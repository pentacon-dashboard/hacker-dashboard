import type { SnapshotResponse } from "@/lib/api/portfolio";

export interface NetworthChartRange {
  from?: string;
  to?: string;
}

export interface NetworthChartPoint {
  date: string;
  time: number;
  value: number;
}

export type NetworthChartDomain = [number, number];

export function parseIsoDateToUtc(value: string | null | undefined): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? "");
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const time = Date.UTC(year, month - 1, day);
  const parsed = new Date(time);

  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null;
  }

  return time;
}

export function buildNetworthChartDomain(
  range?: NetworthChartRange,
): NetworthChartDomain | undefined {
  const from = parseIsoDateToUtc(range?.from);
  const to = parseIsoDateToUtc(range?.to);
  if (from == null || to == null || from > to) return undefined;
  return [from, to];
}

export function buildNetworthChartData(
  snapshots: SnapshotResponse[],
  range?: NetworthChartRange,
): NetworthChartPoint[] {
  const domain = buildNetworthChartDomain(range);

  return snapshots
    .map((snapshot) => {
      const time = parseIsoDateToUtc(snapshot.snapshot_date);
      const value = Number(snapshot.total_value_krw);
      if (time == null || !Number.isFinite(value)) return null;
      return {
        date: snapshot.snapshot_date,
        time,
        value,
      };
    })
    .filter((point): point is NetworthChartPoint => {
      if (!point) return false;
      if (!domain) return true;
      return point.time >= domain[0] && point.time <= domain[1];
    })
    .sort((a, b) => a.time - b.time);
}

export function formatNetworthDateTick(value: number | string): string {
  const time = Number(value);
  if (!Number.isFinite(time)) return String(value);
  return new Date(time).toISOString().slice(5, 10);
}

export function formatNetworthDateLabel(value: number | string): string {
  const time = Number(value);
  if (!Number.isFinite(time)) return String(value);
  return new Date(time).toISOString().slice(0, 10);
}
