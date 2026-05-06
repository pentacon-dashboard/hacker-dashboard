import type {
  HoldingDetail,
  PortfolioSummary,
  SnapshotResponse,
} from "@/lib/api/portfolio";

const MARKET_TO_ASSET_CLASS: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock_us",
  nasdaq: "stock_us",
  nyse: "stock_us",
  naver_kr: "stock_kr",
  krx: "stock_kr",
};

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "국내주식",
  stock_us: "미국주식",
  crypto: "가상자산",
  cash: "현금",
  fx: "외화",
  other: "기타",
};

export const hhiFormulaLabel =
  "자산군별 비중 제곱합(HHI)을 0~100 점수로 환산한 집중도 지표입니다.";

export interface AssetClassEvidenceRow {
  key: string;
  label: string;
  ratio: number;
  valueKrw: number;
}

export interface HoldingWeightRow {
  id: number;
  market: string;
  code: string;
  valueKrw: number;
  pnlPct: number;
  weightPct: number;
}

export interface HoldingDistributionRow {
  key: string;
  label: string;
  count: number;
}

export interface SnapshotPeriodStats {
  startDate: string;
  endDate: string;
  startValueKrw: number;
  endValueKrw: number;
  highValueKrw: number;
  lowValueKrw: number;
  returnPct: number;
}

function toNumber(value: number | string | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function labelAssetClass(key: string): string {
  return ASSET_CLASS_LABELS[key] ?? key;
}

function holdingIdentity(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;

  const record = value as Record<string, unknown>;
  const market = String(record.market ?? "").trim().toLowerCase();
  const code = String(record.code ?? "").trim().toUpperCase();
  const valueKrw = record.value_krw;

  if (!market || !code || valueKrw == null || !Number.isFinite(Number(valueKrw))) {
    return null;
  }

  return `${market}:${code}`;
}

export function classifyMarketAssetClass(market: string): string {
  return MARKET_TO_ASSET_CLASS[market.trim().toLowerCase()] ?? "other";
}

export function buildAssetClassEvidenceRows(
  summary: PortfolioSummary,
): AssetClassEvidenceRow[] {
  const total = toNumber(summary.total_value_krw);

  return Object.entries(summary.asset_class_breakdown)
    .map(([key, ratio]) => {
      const numericRatio = toNumber(ratio);
      return {
        key,
        label: labelAssetClass(key),
        ratio: numericRatio,
        valueKrw: total * numericRatio,
      };
    })
    .sort((a, b) => b.ratio - a.ratio || b.valueKrw - a.valueKrw);
}

export function buildTopHoldingWeightRows(
  holdings: HoldingDetail[],
  totalValueKrw: number,
  limit = 5,
): HoldingWeightRow[] {
  return [...holdings]
    .sort((a, b) => toNumber(b.value_krw) - toNumber(a.value_krw))
    .slice(0, limit)
    .map((holding) => {
      const valueKrw = toNumber(holding.value_krw);

      return {
        id: holding.id,
        market: holding.market,
        code: holding.code,
        valueKrw,
        pnlPct: toNumber(holding.pnl_pct),
        weightPct: totalValueKrw > 0 ? (valueKrw / totalValueKrw) * 100 : 0,
      };
    });
}

export function buildHoldingDistributionRows(
  holdings: HoldingDetail[],
): HoldingDistributionRow[] {
  const counts = new Map<string, number>();

  holdings.forEach((holding) => {
    const key = classifyMarketAssetClass(holding.market);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .map(([key, count]) => ({
      key,
      label: labelAssetClass(key),
      count,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function buildPeriodSnapshotStats(
  snapshots: SnapshotResponse[],
): SnapshotPeriodStats | null {
  const ordered = [...snapshots].sort((a, b) =>
    a.snapshot_date.localeCompare(b.snapshot_date),
  );
  if (ordered.length < 2) return null;

  const start = ordered[0]!;
  const end = ordered[ordered.length - 1]!;
  const values = ordered.map((snapshot) => toNumber(snapshot.total_value_krw));
  const startValueKrw = toNumber(start.total_value_krw);
  const endValueKrw = toNumber(end.total_value_krw);

  return {
    startDate: start.snapshot_date,
    endDate: end.snapshot_date,
    startValueKrw,
    endValueKrw,
    highValueKrw: Math.max(...values),
    lowValueKrw: Math.min(...values),
    returnPct:
      startValueKrw > 0 ? ((endValueKrw - startValueKrw) / startValueKrw) * 100 : 0,
  };
}

export function hasComparableHoldingSnapshots(
  snapshots: SnapshotResponse[],
): boolean {
  const ordered = [...snapshots].sort((a, b) =>
    a.snapshot_date.localeCompare(b.snapshot_date),
  );
  if (ordered.length < 2) return false;

  const first = ordered[0]!;
  const last = ordered[ordered.length - 1]!;
  if (first.holdings_detail.length === 0 || last.holdings_detail.length === 0) {
    return false;
  }

  const firstIds = new Set(
    first.holdings_detail.map(holdingIdentity).filter((id) => id != null),
  );
  const lastIds = new Set(
    last.holdings_detail.map(holdingIdentity).filter((id) => id != null),
  );
  if (firstIds.size === 0 || lastIds.size === 0) return false;

  return Array.from(lastIds).some((id) => firstIds.has(id));
}
