"use client";

import { useState } from "react";
import { notFound } from "next/navigation";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Suspense } from "react";
import { getOhlc, getQuote, type OhlcBar } from "@/lib/api/symbols";
import { listHoldings, type HoldingResponse } from "@/lib/api/portfolio";
import { apiFetch } from "@/lib/api/client";
import { ApiError } from "@/lib/api/client";
import { AssetBadge } from "@/components/common/asset-badge";
import { ChartWrapper } from "@/components/symbol/chart-wrapper";
import { RealtimePrice } from "@/components/symbol/realtime-price";
import { RouterEvidenceModal } from "@/components/symbol/router-evidence-modal";
import { SymbolAnalysisSection } from "@/components/symbol/symbol-analysis-section";
import { TimeframeTabs, type Timeframe } from "@/components/symbol/timeframe-tabs";
import { IndicatorGrid, type IndicatorMetrics } from "@/components/symbol/indicator-grid";
import { IndicatorPanel, type IndicatorBundle } from "@/components/symbol/indicator-panel";
import { IndicatorSubcharts } from "@/components/symbol/indicator-subcharts";
import type { RsiPoint, MacdPoint } from "@/components/symbol/indicator-subcharts";
import { KeyIssueList, type KeyIssue } from "@/components/symbol/key-issue-list";
import { SymbolNewsPanel } from "@/components/symbol/symbol-news-panel";
import { SectionCard } from "@/components/dashboard/section-card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatUSD, formatKRW } from "@/lib/utils/format";
import { useLocale } from "@/lib/i18n/locale-provider";
import { getSymbolDisplayParts } from "@/lib/market/display";

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
  krx: "stock",
  kiwoom: "stock",
};

function formatVolume(volume: number | null | undefined, currency: string) {
  if (volume == null) return "-";
  if (currency === "KRW") {
    if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
    if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  }
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(2)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(2)}K`;
  return volume.toFixed(2);
}

// timeframe → interval 매핑
const TIMEFRAME_TO_INTERVAL: Record<Timeframe, string> = {
  "1m": "1m",
  "5m": "5m",
  "15m": "15m",
  "60m": "60m",
  day: "1d",
  week: "1wk",
  month: "1mo",
};

// BE /market/symbol/{market}/{code}/indicators 실제 응답 스키마
interface BeIndicatorsRaw {
  interval: string;
  period: number;
  rsi_14: Array<{ t: string; v: number }>;
  macd: Array<{ t: string; macd: number; signal: number; histogram: number }>;
  bollinger: {
    upper: Array<{ t: string; v: number }>;
    mid: Array<{ t: string; v: number }>;
    lower: Array<{ t: string; v: number }>;
  };
  stochastic: Array<{ t: string; k: number; d: number }>;
  metrics: {
    rsi_latest: number | null;
    macd_latest: number | null;
    macd_signal: number | null;
    bollinger_position: number | null;
  };
  signal: "buy" | "hold" | "sell";
}

// FE 내부 정규화 타입
interface IndicatorsResponse {
  metrics: IndicatorMetrics;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  bollinger_upper: number | null;
  bollinger_lower: number | null;
  stochastic: number | null;
  signal: "buy" | "hold" | "sell";
  // raw 시계열 — 서브차트용
  rsi_series: RsiPoint[];
  macd_series: MacdPoint[];
}

function calcMa(ohlc: OhlcBar[], period: number): number | null {
  if (ohlc.length < period) return null;
  const slice = ohlc.slice(-period);
  const sum = slice.reduce((s, b) => s + Number(b.close), 0);
  return sum / period;
}

function formatAvgCost(avgCost: string, currency: string): string {
  const n = Number(avgCost);
  if (Number.isNaN(n)) return avgCost;
  if (currency === "KRW") return formatKRW(n);
  return formatUSD(n);
}

function formatMa(val: number | null, currency: string): string | null {
  if (val === null) return null;
  if (currency === "KRW") return formatKRW(val);
  return formatUSD(val);
}

function normalizeIndicators(
  raw: BeIndicatorsRaw,
  changePct: string,
  volume: string,
  ohlc: OhlcBar[],
  currentHolding: HoldingResponse | null,
  currency: string,
): IndicatorsResponse {
  const lastRsi = raw.metrics.rsi_latest ?? (raw.rsi_14.at(-1)?.v ?? null);
  const lastMacd = raw.metrics.macd_latest ?? (raw.macd.at(-1)?.macd ?? null);
  const lastMacdSig = raw.metrics.macd_signal ?? (raw.macd.at(-1)?.signal ?? null);
  const lastBolUpper = raw.bollinger.upper.at(-1)?.v ?? null;
  const lastBolLower = raw.bollinger.lower.at(-1)?.v ?? null;
  const lastSto = raw.stochastic.at(-1)?.k ?? null;

  const ma20Raw = calcMa(ohlc, 20);
  const ma60Raw = calcMa(ohlc, 60);

  const avgCost =
    currentHolding != null
      ? formatAvgCost(currentHolding.avg_cost, currency)
      : null;

  return {
    metrics: {
      change_pct: changePct,
      avg_cost: avgCost,
      ma20: formatMa(ma20Raw, currency),
      ma60: formatMa(ma60Raw, currency),
      volume,
      signal: raw.signal,
    },
    rsi_14: lastRsi,
    macd: lastMacd,
    macd_signal: lastMacdSig,
    bollinger_upper: lastBolUpper,
    bollinger_lower: lastBolLower,
    stochastic: lastSto,
    signal: raw.signal,
    rsi_series: raw.rsi_14,
    macd_series: raw.macd,
  };
}

// 목업 stub 이슈
const STUB_ISSUES: KeyIssue[] = [
  {
    id: "1",
    title: "실적 발표 예정 — 어닝 서프라이즈 가능성",
    severity: "high",
    date: "2026-04-28",
  },
  {
    id: "2",
    title: "기관 투자자 지분 변동 공시",
    severity: "medium",
    date: "2026-04-25",
  },
  {
    id: "3",
    title: "섹터 내 경쟁사 신제품 발표",
    severity: "low",
    date: "2026-04-22",
  },
];

export default function SymbolDetailPage() {
  const { t } = useLocale();
  const params = useParams<{ market: string; code: string }>();
  const decodedMarket = decodeURIComponent(params.market);
  const decodedCode = decodeURIComponent(params.code);
  const displaySymbol = getSymbolDisplayParts(decodedMarket, decodedCode);
  const headerMeta = displaySymbol.secondary ?? decodedMarket;

  const [timeframe, setTimeframe] = useState<Timeframe>("day");

  const interval = TIMEFRAME_TO_INTERVAL[timeframe] ?? "1d";

  const quoteQuery = useQuery({
    queryKey: ["symbol", "quote", decodedMarket, decodedCode],
    queryFn: async () => {
      try {
        return await getQuote(decodedMarket, decodedCode);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          notFound();
        }
        return null;
      }
    },
    staleTime: 10_000,
  });

  const ohlcQuery = useQuery<OhlcBar[]>({
    queryKey: ["symbol", "ohlc", decodedMarket, decodedCode, interval],
    queryFn: async () => {
      try {
        return await getOhlc(decodedMarket, decodedCode, "1d", 180);
      } catch {
        return [];
      }
    },
    staleTime: 30_000,
  });

  const holdingsQuery = useQuery<HoldingResponse[]>({
    queryKey: ["portfolio", "holdings"],
    queryFn: async () => {
      try {
        return await listHoldings();
      } catch {
        return [];
      }
    },
    staleTime: 60_000,
  });

  const assetClass = ASSET_CLASS_MAP[decodedMarket] ?? "macro";
  const currency = quoteQuery.data?.currency ?? (decodedMarket === "upbit" ? "KRW" : "USD");

  const currentHolding =
    holdingsQuery.data?.find(
      (h) => h.market === decodedMarket && h.code === decodedCode,
    ) ?? null;

  const indicatorsQuery = useQuery<IndicatorsResponse | null>({
    queryKey: [
      "symbol",
      "indicators",
      decodedMarket,
      decodedCode,
      timeframe,
      quoteQuery.data?.change_pct,
      quoteQuery.data?.volume,
      ohlcQuery.data?.length,
      currentHolding?.avg_cost,
    ],
    queryFn: async () => {
      const quote = quoteQuery.data;
      const changePct =
        quote?.change_pct != null
          ? String(quote.change_pct)
          : "0";
      const volumeRaw = quote?.volume;
      const volumeStr =
        volumeRaw != null
          ? formatVolume(Number(volumeRaw), currency)
          : "-";
      const ohlc = ohlcQuery.data ?? [];
      try {
        const raw = await apiFetch<BeIndicatorsRaw>(
          `/market/symbol/${encodeURIComponent(decodedMarket)}/${encodeURIComponent(decodedCode)}/indicators?interval=${timeframe}&period=60`,
        );
        return normalizeIndicators(raw, changePct, volumeStr, ohlc, currentHolding, currency);
      } catch {
        // BE 오류 시 stub fallback — 페이지 crash 방지
        const ma20Raw = calcMa(ohlc, 20);
        const ma60Raw = calcMa(ohlc, 60);
        return {
          metrics: {
            change_pct: changePct,
            avg_cost:
              currentHolding != null
                ? formatAvgCost(currentHolding.avg_cost, currency)
                : null,
            ma20: formatMa(ma20Raw, currency),
            ma60: formatMa(ma60Raw, currency),
            volume: volumeStr,
            signal: "hold" as const,
          },
          rsi_14: null,
          macd: null,
          macd_signal: null,
          bollinger_upper: null,
          bollinger_lower: null,
          stochastic: null,
          signal: "hold" as const,
          rsi_series: [],
          macd_series: [],
        };
      }
    },
    staleTime: 30_000,
  });

  const indicatorBundle: IndicatorBundle | null = indicatorsQuery.data
    ? {
        rsi_14: indicatorsQuery.data.rsi_14,
        macd: indicatorsQuery.data.macd,
        macd_signal: indicatorsQuery.data.macd_signal,
        bollinger_upper: indicatorsQuery.data.bollinger_upper,
        bollinger_lower: indicatorsQuery.data.bollinger_lower,
        stochastic: indicatorsQuery.data.stochastic,
        signal: indicatorsQuery.data.signal,
      }
    : null;

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{displaySymbol.primary}</h1>
            <AssetBadge assetClass={assetClass} />
            <span className="text-sm text-muted-foreground">{headerMeta}</span>
          </div>
          {quoteQuery.data ? (
            <Suspense
              fallback={
                <div className="h-10 w-48 animate-pulse rounded bg-muted" />
              }
            >
              <RealtimePrice
                market={decodedMarket}
                code={decodedCode}
                initialQuote={quoteQuery.data}
              />
            </Suspense>
          ) : quoteQuery.isLoading ? (
            <Skeleton className="h-10 w-48" />
          ) : (
            <p className="text-sm text-muted-foreground">{t("symbol.noPrice")}</p>
          )}
        </div>
      </div>

      {/* 타임프레임 탭 */}
      <TimeframeTabs value={timeframe} onChange={setTimeframe} />

      {/* 메인 그리드 */}
      <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
        {/* 차트 + 인디케이터 그리드 */}
        <div className="space-y-4">
          <div>
            <h2 className="mb-2 text-sm font-semibold text-muted-foreground">
              {timeframe === "day" ? t("symbol.chart.daily") : timeframe === "week" ? t("symbol.chart.weekly") : timeframe === "month" ? t("symbol.chart.monthly") : `${timeframe} ${t("symbol.chart.suffix")}`} (MA20 / MA60)
            </h2>
            {ohlcQuery.isLoading ? (
              <Skeleton className="h-[400px] w-full" />
            ) : (ohlcQuery.data?.length ?? 0) > 0 ? (
              <ChartWrapper
                data={ohlcQuery.data!}
                market={decodedMarket}
                code={decodedCode}
              />
            ) : (
              <div
                className="flex h-[400px] items-center justify-center rounded-lg border bg-muted/30 text-sm text-muted-foreground"
                role="status"
              >
                {t("symbol.noChart")}
              </div>
            )}
          </div>

          {/* RSI / MACD 서브차트 */}
          <IndicatorSubcharts
            rsi={indicatorsQuery.data?.rsi_series ?? []}
            macd={indicatorsQuery.data?.macd_series ?? []}
            isLoading={indicatorsQuery.isLoading}
          />

          {/* 지표 카드 6개 */}
          <IndicatorGrid
            metrics={indicatorsQuery.data?.metrics ?? null}
            isLoading={indicatorsQuery.isLoading}
          />
        </div>

        {/* 우측 사이드패널 */}
        <aside className="space-y-4">
          {/* 기본 정보 */}
          <div className="rounded-lg border p-4 space-y-3">
            <h2 className="text-sm font-semibold">{t("symbol.basicInfo")}</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">{t("symbol.info.exchange")}</dt>
                <dd className="font-medium">{decodedMarket}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">{t("symbol.info.currency")}</dt>
                <dd className="font-medium">{currency}</dd>
              </div>
              {quoteQuery.data?.volume != null && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">{t("symbol.info.volume")}</dt>
                  <dd className="font-medium tabular-nums">
                    {formatVolume(quoteQuery.data.volume, currency)}
                  </dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-muted-foreground">{t("symbol.info.assetClass")}</dt>
                <dd>
                  <AssetBadge assetClass={assetClass} />
                </dd>
              </div>
            </dl>
          </div>

          {/* 기술 지표 리스트 */}
          <SectionCard title={t("symbol.technicalIndicators")} testId="symbol-indicator-panel">
            <IndicatorPanel
              bundle={indicatorBundle}
              isLoading={indicatorsQuery.isLoading}
            />
          </SectionCard>

          {/* 주요 이슈 */}
          <SectionCard title={t("symbol.keyIssues")} testId="symbol-key-issues">
            <KeyIssueList issues={STUB_ISSUES} />
          </SectionCard>

          {/* Router 결정 근거 */}
          <RouterEvidenceModal market={decodedMarket} code={decodedCode} />
        </aside>
      </div>

      {/* 하단: 뉴스 + AI 분석 */}
      <section className="grid gap-5 lg:grid-cols-2">
        <SectionCard title={t("symbol.relatedNews")} testId="symbol-news-section">
          <SymbolNewsPanel symbol={decodedCode} limit={5} />
        </SectionCard>

        <section aria-labelledby="analysis-section-heading">
          <h2
            id="analysis-section-heading"
            className="mb-3 text-sm font-semibold text-muted-foreground"
          >
            {t("symbol.aiAnalysis")}
          </h2>
          <SymbolAnalysisSection market={decodedMarket} code={decodedCode} />
        </section>
      </section>
    </div>
  );
}
