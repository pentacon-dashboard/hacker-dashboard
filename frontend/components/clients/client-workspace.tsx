"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BarChart3,
  Layers,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SectionCard } from "@/components/dashboard/section-card";
import { Skeleton } from "@/components/ui/skeleton";
import { AddHoldingDialog } from "@/components/portfolio/add-holding-dialog";
import { AiInsightCard } from "@/components/portfolio/ai-insight-card";
import { AssetPieChart } from "@/components/portfolio/asset-pie-chart";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { MonthlyReturnCalendar } from "@/components/portfolio/monthly-return-calendar";
import { RebalancePanel } from "@/components/portfolio/rebalance-panel";
import { SectorHeatmap } from "@/components/portfolio/sector-heatmap";
import { useDataSettings } from "@/lib/hooks/use-data-settings";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getAiInsight,
  getMonthlyReturns,
  getPortfolioClients,
  getPortfolioSummary,
  getSectorHeatmap,
} from "@/lib/api/portfolio";
import {
  formatKRWCompact,
  formatPct,
  formatSignedNumber,
  signedColorClass,
} from "@/lib/utils/format";
import { getDisplayableHoldings } from "@/lib/portfolio/display-safety";

interface ClientWorkspaceProps {
  clientId: string;
}

export function ClientWorkspace({ clientId }: ClientWorkspaceProps) {
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();
  const currentYear = new Date().getFullYear();

  const clientsQuery = useQuery({
    queryKey: ["portfolio", "clients"],
    queryFn: getPortfolioClients,
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary", clientId],
    queryFn: () => getPortfolioSummary(undefined, clientId),
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const heatmapQuery = useQuery({
    queryKey: ["portfolio", "sectors", "heatmap", clientId],
    queryFn: () => getSectorHeatmap(clientId),
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const calendarQuery = useQuery({
    queryKey: ["portfolio", "monthly-returns", currentYear, clientId],
    queryFn: () => getMonthlyReturns(currentYear, clientId),
    staleTime: 300_000,
  });

  const insightQuery = useQuery({
    queryKey: ["portfolio", "ai-insight", clientId],
    queryFn: () => getAiInsight(clientId),
    staleTime: 300_000,
  });

  const summary = summaryQuery.data;
  const clientRows = clientsQuery.data?.clients ?? [];
  const selectedClient = clientRows.find((client) => client.client_id === clientId);
  const clientName = selectedClient?.client_name ?? summary?.client_name ?? clientId;
  const displayHoldings = useMemo(
    () => getDisplayableHoldings(summary?.holdings ?? []),
    [summary?.holdings],
  );
  const hiddenHoldingCount = Math.max(
    0,
    (summary?.holdings.length ?? 0) - displayHoldings.length,
  );

  function handleRetry() {
    void clientsQuery.refetch();
    void summaryQuery.refetch();
    void heatmapQuery.refetch();
    void calendarQuery.refetch();
    void insightQuery.refetch();
  }

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <Link
          href="/"
          className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          data-testid="client-workspace-back"
        >
          <ArrowLeft className="h-4 w-4" />
          고객장부
        </Link>
        <h1 className="truncate text-2xl font-bold tracking-tight">
          {clientName} 워크스페이스
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          고객 ID: <span className="font-medium">{clientId}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <AddHoldingDialog clientId={clientId} />
      </div>
    </div>
  );

  if (summaryQuery.isLoading) {
    return (
      <div className="space-y-6" data-testid="client-workspace-loading">
        {header}
        <div className="grid gap-4 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="rounded-xl border bg-card p-4 shadow-sm">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-3 h-6 w-24" />
            </div>
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (summaryQuery.isError) {
    return (
      <div className="space-y-6" data-testid="client-workspace-error">
        {header}
        <ErrorState
          title={t("portfolio.loadError")}
          description={t("portfolio.loadErrorDesc")}
          onRetry={handleRetry}
        />
      </div>
    );
  }

  if (!summary || summary.holdings.length === 0) {
    return (
      <div className="space-y-6" data-testid="client-workspace">
        {header}
        <EmptyState
          title={t("portfolio.emptyTitle")}
          description={t("portfolio.emptyDesc")}
          action={<AddHoldingDialog clientId={clientId} />}
        />
      </div>
    );
  }

  const totalPnlColorClass = signedColorClass(summary.total_pnl_krw);
  const dailyColorClass = signedColorClass(summary.daily_change_krw);
  const rawSummary = summary as typeof summary & { win_rate_pct?: string };
  const winRatePct = rawSummary.win_rate_pct
    ? Number(rawSummary.win_rate_pct)
    : (summary.holdings.filter((holding) => Number(holding.pnl_pct) > 0).length /
        Math.max(summary.holdings.length, 1)) *
      100;
  const hasOnlyCorruptedHoldings =
    summary.holdings.length > 0 && displayHoldings.length === 0;

  if (hasOnlyCorruptedHoldings) {
    return (
      <div className="space-y-6" data-testid="client-workspace">
        {header}
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">{t("common.dataCorruptedTitle")}</p>
          <p className="mt-1 text-xs text-amber-800">
            가격 또는 통화 데이터가 안전하게 표시되지 않아 {hiddenHoldingCount}개 보유종목을 숨겼습니다.
          </p>
        </div>
        <EmptyState
          title="표시 가능한 보유종목이 없습니다"
          description="손상된 보유 데이터를 정리하거나 새 보유자산을 추가하면 포트폴리오 분석을 다시 볼 수 있습니다."
          action={<AddHoldingDialog clientId={clientId} />}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="client-workspace">
      {header}

      <section
        aria-label={t("portfolio.kpiAria")}
        className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
      >
        <KpiCard
          label={t("portfolio.kpi.totalValue")}
          value={formatKRWCompact(summary.total_value_krw)}
          delta={t("portfolio.krwEquiv")}
          icon={<Wallet className="h-4 w-4" />}
          accent="blue"
          testId="portfolio-kpi-total"
        />
        <KpiCard
          label={t("portfolio.kpi.totalPnl")}
          value={`${formatSignedNumber(summary.total_pnl_krw).replace(
            /[+-]/,
            (sign) => (sign === "+" ? "+" : "-"),
          )} KRW`}
          delta={formatPct(summary.total_pnl_pct, { signed: true })}
          deltaValue={Number(summary.total_pnl_pct)}
          icon={<TrendingUp className="h-4 w-4" />}
          accent={Number(summary.total_pnl_pct) >= 0 ? "green" : "rose"}
          testId="portfolio-kpi-pnl"
        />
        <KpiCard
          label={t("portfolio.kpi.dailyChange")}
          value={formatPct(summary.daily_change_pct, { signed: true })}
          delta={`${Number(summary.daily_change_krw) > 0 ? "+" : ""}${formatKRWCompact(
            summary.daily_change_krw,
          )}`}
          deltaValue={Number(summary.daily_change_pct)}
          icon={<BarChart3 className="h-4 w-4" />}
          accent="violet"
          testId="portfolio-kpi-daily"
        />
        <KpiCard
          label={t("portfolio.kpi.holdings")}
          value={`${summary.holdings_count}`}
          delta={t("dashboard.kpi.holdingsUnit")}
          icon={<Layers className="h-4 w-4" />}
          accent="slate"
          testId="portfolio-kpi-holdings-count"
        />
        <KpiCard
          label={t("portfolio.kpi.winRate")}
          value={`${winRatePct.toFixed(1)}%`}
          delta={
            winRatePct >= 60
              ? t("portfolio.winRate.good")
              : winRatePct >= 40
                ? t("portfolio.winRate.fair")
                : t("portfolio.winRate.poor")
          }
          tone={winRatePct >= 60 ? "positive" : winRatePct >= 40 ? "neutral" : "negative"}
          icon={<Target className="h-4 w-4" />}
          accent="amber"
          testId="portfolio-kpi-win-rate"
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("portfolio.allocation")}
          className="lg:col-span-4"
          testId="portfolio-section-allocation"
        >
          <AssetPieChart breakdown={summary.asset_class_breakdown} />
          <div className="mt-4 space-y-2 border-t pt-4">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{t("portfolio.totalReturn")}</span>
              <span className={`font-bold tabular-nums ${totalPnlColorClass}`}>
                {formatPct(summary.total_pnl_pct, { signed: true })}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full ${
                  Number(summary.total_pnl_pct) >= 0 ? "bg-emerald-500" : "bg-red-500"
                }`}
                style={{
                  width: `${Math.min(Math.abs(Number(summary.total_pnl_pct)) * 5, 100)}%`,
                }}
              />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{t("portfolio.kpi.dailyChange")}</span>
              <span className={`font-semibold tabular-nums ${dailyColorClass}`}>
                {formatPct(summary.daily_change_pct, { signed: true })}
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title={t("portfolio.holdingsOverview")}
          className="lg:col-span-8"
          testId="portfolio-section-holdings"
        >
          {hiddenHoldingCount > 0 && (
            <p className="mb-3 text-xs text-muted-foreground">
              가격 또는 통화 데이터가 안전하게 표시되지 않아 {hiddenHoldingCount}개 보유종목을 숨겼습니다.
            </p>
          )}
          <HoldingsTable holdings={displayHoldings} />
        </SectionCard>
      </section>

      <SectionCard title={t("portfolio.sectorHeatmap")} testId="portfolio-section-heatmap">
        {heatmapQuery.isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : heatmapQuery.isError ? (
          <p className="text-sm text-muted-foreground">{t("portfolio.sectorLoadFail")}</p>
        ) : (
          <SectorHeatmap tiles={heatmapQuery.data ?? []} />
        )}
      </SectionCard>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("portfolio.monthlyCalendar")}
          className="lg:col-span-8"
          testId="portfolio-section-calendar"
        >
          {calendarQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <MonthlyReturnCalendar cells={calendarQuery.data ?? []} year={currentYear} />
          )}
        </SectionCard>

        <SectionCard
          title={t("portfolio.aiInsight")}
          className="lg:col-span-4"
          testId="portfolio-section-insight"
        >
          <AiInsightCard
            insight={insightQuery.data ?? null}
            isLoading={insightQuery.isLoading}
          />
        </SectionCard>
      </section>

      <section
        aria-labelledby="portfolio-rebalance-title"
        className="space-y-4"
        data-testid="portfolio-section-rebalance"
      >
        <h2 id="portfolio-rebalance-title" className="text-sm font-semibold tracking-tight">
          {t("portfolio.rebalance")}
        </h2>
        <RebalancePanel clientId={clientId} />
      </section>
    </div>
  );
}
