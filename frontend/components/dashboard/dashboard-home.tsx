"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeDollarSign,
  Layers,
  LineChart as LineChartIcon,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  AllocationBreakdown,
  type AllocationSlice,
} from "@/components/dashboard/allocation-breakdown";
import { DimensionBars } from "@/components/dashboard/dimension-bars";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { MarketLeaders } from "@/components/dashboard/market-leaders";
import { NewsPanel } from "@/components/dashboard/news-panel";
import {
  PERIOD_DAYS,
  PeriodTabs,
  type PeriodKey,
} from "@/components/dashboard/period-tabs";
import { RiskGauge } from "@/components/dashboard/risk-gauge";
import { SectionCard } from "@/components/dashboard/section-card";
import { TopHoldingsTable } from "@/components/dashboard/top-holdings-table";
import { ErrorState } from "@/components/common/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { NetworthChart } from "@/components/portfolio/networth-chart";
import { useDataSettings } from "@/lib/hooks/use-data-settings";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getPortfolioSummary,
  getSnapshots,
} from "@/lib/api/portfolio";
import {
  buildDashboardNewsQuery,
  getDisplayableHoldings,
  getDisplayableHoldingSymbols,
} from "@/lib/portfolio/display-safety";
import {
  formatKRWCompact,
  formatPct,
} from "@/lib/utils/format";

const ASSET_CLASS_LABEL_KEYS: Record<string, string> = {
  stock_kr: "dashboard.alloc.stockKr",
  stock_us: "dashboard.alloc.stockUs",
  crypto: "dashboard.alloc.crypto",
  cash: "dashboard.alloc.cash",
  fx: "dashboard.alloc.fx",
  other: "dashboard.alloc.other",
};

const ASSET_CLASS_COLORS: Record<string, string> = {
  stock_kr: "#3b82f6",
  stock_us: "#6366f1",
  crypto: "#f59e0b",
  cash: "#10b981",
  fx: "#06b6d4",
  other: "#94a3b8",
};

function formatDate(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function rangeForPeriod(period: PeriodKey) {
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - PERIOD_DAYS[period]);
  return {
    from: formatDate(from),
    to: formatDate(to),
    label: `${formatDate(from)} ~ ${formatDate(to)}`,
  };
}

interface SelectedClientDashboardProps {
  clientId: string;
  clientName?: string;
}

export function SelectedClientDashboard({
  clientId,
  clientName,
}: SelectedClientDashboardProps) {
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();
  const [period, setPeriod] = useState<PeriodKey>("1M");
  const range = useMemo(() => rangeForPeriod(period), [period]);

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary", period, clientId],
    queryFn: () => getPortfolioSummary(PERIOD_DAYS[period], clientId),
    enabled: clientId.length > 0,
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const snapshotsQuery = useQuery({
    queryKey: ["portfolio", "snapshots", period, clientId],
    queryFn: () => getSnapshots(range.from, range.to, clientId),
    enabled: clientId.length > 0,
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const summary = summaryQuery.data ?? null;
  const displayName = clientName ?? summary?.client_name ?? clientId;
  const isLoading = summaryQuery.isLoading;
  const displayHoldings = useMemo(
    () => getDisplayableHoldings(summary?.holdings ?? []),
    [summary?.holdings],
  );
  const hiddenHoldingCount = Math.max(
    0,
    (summary?.holdings.length ?? 0) - displayHoldings.length,
  );
  const newsSymbols = useMemo(
    () => getDisplayableHoldingSymbols(summary?.holdings ?? []),
    [summary?.holdings],
  );
  const newsQuery = useMemo(
    () => buildDashboardNewsQuery(summary?.holdings ?? []),
    [summary?.holdings],
  );

  const allocationSlices = useMemo<AllocationSlice[]>(() => {
    if (!summary) return [];
    const total = Number(summary.total_value_krw);
    return Object.entries(summary.asset_class_breakdown)
      .map(([key, ratio]) => {
        const r = Number(ratio);
        return {
          key,
          name: ASSET_CLASS_LABEL_KEYS[key] ? t(ASSET_CLASS_LABEL_KEYS[key]!) : key,
          ratio: r,
          value_krw: Number.isFinite(total) ? total * r : 0,
          color: ASSET_CLASS_COLORS[key] ?? ASSET_CLASS_COLORS.other!,
        };
      })
      .sort((a, b) => b.ratio - a.ratio);
  }, [summary, t]);

  function retryDashboard() {
    void summaryQuery.refetch();
    void snapshotsQuery.refetch();
  }

  return (
    <div className="space-y-5" data-testid="dashboard-home">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("dashboard.title")}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {displayName
              ? `${displayName} 고객 포트폴리오 대시보드`
              : t("dashboard.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodTabs value={period} onChange={setPeriod} />
          <span
            className="rounded-md border bg-card px-3 py-1 text-xs text-muted-foreground tabular-nums"
            data-testid="dashboard-date-range"
          >
            {range.label}
          </span>
        </div>
      </div>

      {summaryQuery.isError ? (
        <ErrorState
          title="대시보드 데이터 로드 실패"
          description="선택 고객의 포트폴리오 요약을 불러오지 못했습니다."
          onRetry={retryDashboard}
        />
      ) : null}

      <section
        aria-label="핵심 지표"
        className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6"
      >
        {isLoading || !summary ? (
          Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="rounded-xl border bg-card p-4 shadow-sm">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-3 h-6 w-24" />
            </div>
          ))
        ) : (
          <>
            <KpiCard
              label={t("dashboard.kpi.totalAssets")}
              value={formatKRWCompact(summary.total_value_krw)}
              delta={formatPct(summary.total_pnl_pct, { signed: true })}
              deltaValue={Number(summary.total_pnl_pct)}
              icon={<Wallet className="h-4 w-4" />}
              accent="blue"
              testId="kpi-total-value"
            />
            <KpiCard
              label={t("dashboard.kpi.dailyChange")}
              value={formatPct(summary.daily_change_pct, { signed: true })}
              delta={`${Number(summary.daily_change_krw) > 0 ? "+" : ""}${formatKRWCompact(
                summary.daily_change_krw,
              )}`}
              deltaValue={Number(summary.daily_change_pct)}
              icon={<TrendingUp className="h-4 w-4" />}
              accent="green"
              testId="kpi-daily-change"
            />
            <KpiCard
              label={t("dashboard.kpi.monthlyChange")}
              value={formatPct(summary.period_change_pct, { signed: true })}
              deltaValue={Number(summary.period_change_pct)}
              icon={<LineChartIcon className="h-4 w-4" />}
              accent="violet"
              testId="kpi-period-change"
            />
            <KpiCard
              label={t("dashboard.kpi.holdings")}
              value={`${summary.holdings_count}`}
              delta={t("dashboard.kpi.holdingsUnit")}
              icon={<Layers className="h-4 w-4" />}
              accent="slate"
              testId="kpi-holdings-count"
            />
            <KpiCard
              label={t("dashboard.kpi.todayPnl")}
              value={formatKRWCompact(summary.daily_change_krw)}
              delta={formatPct(summary.daily_change_pct, { signed: true })}
              deltaValue={Number(summary.daily_change_pct)}
              icon={<BadgeDollarSign className="h-4 w-4" />}
              accent="rose"
              testId="kpi-today-pnl"
            />
            <KpiCard
              label={t("dashboard.kpi.concentration")}
              value={formatPct(summary.risk_score_pct)}
              delta={
                Number(summary.risk_score_pct) >= 66
                  ? t("dashboard.risk.high")
                  : Number(summary.risk_score_pct) >= 33
                    ? t("dashboard.risk.medium")
                    : t("dashboard.risk.low")
              }
              tone={
                Number(summary.risk_score_pct) >= 66
                  ? "negative"
                  : Number(summary.risk_score_pct) >= 33
                    ? "neutral"
                    : "positive"
              }
              icon={<AlertTriangle className="h-4 w-4" />}
              accent="amber"
              testId="kpi-risk-score"
            />
          </>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("dashboard.assetTrend")}
          className="lg:col-span-5"
          testId="section-networth"
          action={
            <span className="text-xs text-muted-foreground">
              {PERIOD_DAYS[period]}일
            </span>
          }
        >
          {snapshotsQuery.isLoading ? (
            <Skeleton className="h-56 w-full" />
          ) : (
            <NetworthChart snapshots={snapshotsQuery.data ?? []} />
          )}
        </SectionCard>

        <SectionCard
          title={t("dashboard.allocation")}
          className="lg:col-span-4"
          testId="section-allocation"
        >
          {isLoading ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <AllocationBreakdown data={allocationSlices} />
          )}
        </SectionCard>

        <SectionCard
          title={t("dashboard.concentrationRisk")}
          className="lg:col-span-3"
          testId="section-risk"
        >
          {isLoading || !summary ? (
            <div className="flex h-48 items-center justify-center">
              <Skeleton className="h-40 w-40 rounded-full" />
            </div>
          ) : (
            <RiskGauge score={Number(summary.risk_score_pct)} />
          )}
        </SectionCard>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("dashboard.top5Holdings")}
          className="lg:col-span-4"
          testId="section-top-holdings"
        >
          {isLoading || !summary ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <>
              {hiddenHoldingCount > 0 && (
                <p className="mb-3 text-xs text-muted-foreground">
                  일부 보유 종목은 심볼 또는 통화 데이터가 올바르지 않아 숨김 처리되었습니다.
                </p>
              )}
              <TopHoldingsTable
                holdings={displayHoldings}
                limit={5}
                totalValueKrw={Number(summary.total_value_krw)}
                showAvgCost
                showCurrentPrice
              />
            </>
          )}
        </SectionCard>

        <SectionCard
          title={t("dashboard.dimensionAnalysis")}
          className="lg:col-span-5"
          testId="section-dimension"
        >
          {isLoading || !summary ? (
            <Skeleton className="h-56 w-full" />
          ) : (
            <DimensionBars data={summary.dimension_breakdown ?? []} />
          )}
        </SectionCard>

        <SectionCard
          title={t("dashboard.marketLeaders")}
          className="lg:col-span-3"
          testId="section-market-leaders"
        >
          <MarketLeaders limit={5} />
        </SectionCard>
      </section>

      <SectionCard
        title={t("dashboard.latestNews")}
        testId="section-news-card"
        action={<span className="text-xs text-muted-foreground">보유 종목 연관 기사</span>}
      >
        <NewsPanel symbols={newsSymbols} query={newsQuery ?? "market"} limit={5} />
      </SectionCard>
    </div>
  );
}

export function DashboardHome() {
  return <SelectedClientDashboard clientId="client-001" />;
}
