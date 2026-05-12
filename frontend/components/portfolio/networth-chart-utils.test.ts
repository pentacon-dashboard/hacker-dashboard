import { describe, expect, it } from "vitest";
import type { SnapshotResponse } from "@/lib/api/portfolio";
import {
  buildNetworthChartData,
  buildNetworthChartDomain,
  formatNetworthDateLabel,
  formatNetworthDateTick,
} from "./networth-chart-utils";

function snapshot(
  snapshotDate: string,
  totalValueKrw: string,
  id = 1,
): SnapshotResponse {
  return {
    id,
    user_id: "pb-demo",
    client_id: "client-001",
    client_name: "Client A",
    snapshot_date: snapshotDate,
    total_value_krw: totalValueKrw,
    total_pnl_krw: "0",
    asset_class_breakdown: {},
    holdings_detail: [],
    created_at: `${snapshotDate}T00:00:00Z`,
  };
}

describe("networth chart utils", () => {
  it("sorts valid snapshot points by date and drops invalid values", () => {
    const data = buildNetworthChartData([
      snapshot("2026-05-12", "12000000", 3),
      snapshot("not-a-date", "11000000", 2),
      snapshot("2026-05-10", "not-a-number", 4),
      snapshot("2026-05-01", "10000000", 1),
    ]);

    expect(data.map((point) => point.date)).toEqual(["2026-05-01", "2026-05-12"]);
    expect(data.map((point) => point.value)).toEqual([10000000, 12000000]);
  });

  it("uses the selected period as the chart domain even when snapshots cover less time", () => {
    const domain = buildNetworthChartDomain({
      from: "2025-05-12",
      to: "2026-05-12",
    });
    const data = buildNetworthChartData(
      [
        snapshot("2025-04-30", "8000000", 1),
        snapshot("2026-04-12", "9000000", 2),
        snapshot("2026-04-25", "10000000", 3),
      ],
      { from: "2025-05-12", to: "2026-05-12" },
    );

    expect(domain).toEqual([
      Date.UTC(2025, 4, 12),
      Date.UTC(2026, 4, 12),
    ]);
    expect(data.map((point) => point.date)).toEqual(["2026-04-12", "2026-04-25"]);
  });

  it("formats numeric time values for axis ticks and tooltips", () => {
    const time = Date.UTC(2026, 4, 12);

    expect(formatNetworthDateTick(time)).toBe("05-12");
    expect(formatNetworthDateLabel(time)).toBe("2026-05-12");
  });
});
