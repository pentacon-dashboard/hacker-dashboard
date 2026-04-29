"use client";

import { useQuery } from "@tanstack/react-query";
import { Wallet, TrendingUp, BarChart3, Layers, Target } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SectionCard } from "@/components/dashboard/section-card";
import { AddHoldingDialog } from "@/components/portfolio/add-holding-dialog";
import { AssetPieChart } from "@/components/portfolio/asset-pie-chart";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { SectorHeatmap } from "@/components/portfolio/sector-heatmap";
import { MonthlyReturnCalendar } from "@/components/portfolio/monthly-return-calendar";
import { AiInsightCard } from "@/components/portfolio/ai-insight-card";
import { RebalancePanel } from "@/components/portfolio/rebalance-panel";
import { useLocale } from "@/lib/i18n/locale-provider";
import { useDataSettings } from "@/lib/hooks/use-data-settings";
import {
  getPortfolioSummary,
  getSectorHeatmap,
  getMonthlyReturns,
  getAiInsight,
} from "@/lib/api/portfolio";
import {
  formatKRWCompact,
  formatPct,
  formatSignedNumber,
  signedColorClass,
} from "@/lib/utils/format";

export const dynamic = "force-dynamic";

export default function PortfolioPage() {
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: () => getPortfolioSummary(),
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const heatmapQuery = useQuery({
    queryKey: ["portfolio", "sectors", "heatmap"],
    queryFn: getSectorHeatmap,
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const calendarQuery = useQuery({
    queryKey: ["portfolio", "monthly-returns"],
    queryFn: () => getMonthlyReturns(new Date().getFullYear()),
    staleTime: 300_000,
  });

  const insightQuery = useQuery({
    queryKey: ["portfolio", "ai-insight"],
    queryFn: getAiInsight,
    staleTime: 300_000,
  });

  const isLoading = summaryQuery.isLoading;
  const isError = summaryQuery.isError;

  function handleRetry() {
    void summaryQuery.refetch();
    void heatmapQuery.refetch();
    void calendarQuery.refetch();
    void insightQuery.refetch();
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("portfolio.subtitle")}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="rounded-xl border bg-card p-4 shadow-sm">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-3 h-6 w-24" />
            </div>
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
        </div>
        <ErrorState
          title={t("portfolio.loadError")}
          description={t("portfolio.loadErrorDesc")}
          onRetry={handleRetry}
        />
      </div>
    );
  }

  const summary = summaryQuery.data;

  if (!summary || summary.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
            <p className="text-sm text-muted-foreground">{t("portfolio.subtitle")}</p>
          </div>
          <AddHoldingDialog />
        </div>
        <EmptyState
          title={t("portfolio.emptyTitle")}
          description={t("portfolio.emptyDesc")}
          action={<AddHoldingDialog />}
        />
      </div>
    );
  }

  const totalPnlColorClass = signedColorClass(summary.total_pnl_krw);
  const dailyColorClass = signedColorClass(summary.daily_change_krw);

  // win_rate_pct: BE 가 추가하면 직접 사용, 없으면 holdings 에서 계산
  const rawSummary = summary as typeof summary & { win_rate_pct?: string };
  const winRatePct = rawSummary.win_rate_pct
    ? Number(rawSummary.win_rate_pct)
    : summary.holdings.filter((h: { pnl_pct: string | number }) => Number(h.pnl_pct) > 0).length /
      Math.max(summary.holdings.length, 1) * 100;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("portfolio.subtitle")}</p>
        </div>
        <AddHoldingDialog />
      </div>

      {/* KPI 5개 */}
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
          value={formatSignedNumber(summary.total_pnl_krw).replace(/[+-]/, (s) => s === "+" ? "+" : "-") + " KRW"}
          delta={formatPct(summary.total_pnl_pct, { signed: true })}
          deltaValue={Number(summary.total_pnl_pct)}
          icon={<TrendingUp className="h-4 w-4" />}
          accent={Number(summary.total_pnl_pct) >= 0 ? "green" : "rose"}
          testId="portfolio-kpi-pnl"
        />
        <KpiCard
          label={t("portfolio.kpi.dailyChange")}
          value={formatPct(summary.daily_change_pct, { signed: true })}
          delta={(() => {
            const krw = Number(summary.daily_change_krw);
            return (krw > 0 ? "+" : "") + formatKRWCompact(krw);
          })()}
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
          delta={winRatePct >= 60 ? t("portfolio.winRate.good") : winRatePct >= 40 ? t("portfolio.winRate.fair") : t("portfolio.winRate.poor")}
          tone={winRatePct >= 60 ? "positive" : winRatePct >= 40 ? "neutral" : "negative"}
          icon={<Target className="h-4 w-4" />}
          accent="amber"
          testId="portfolio-kpi-win-rate"
        />
      </section>

      {/* 중단: 자산 구성 (도넛) + 보유 종목 테이블 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("portfolio.allocation")}
          className="lg:col-span-4"
          testId="portfolio-section-allocation"
        >
          <AssetPieChart breakdown={summary.asset_class_breakdown} />
          {/* 총 손익률 게이지 */}
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
          <HoldingsTable holdings={summary.holdings} />
        </SectionCard>
      </section>

      {/* 하단: 섹터 히트맵 */}
      <SectionCard
        title={t("portfolio.sectorHeatmap")}
        testId="portfolio-section-heatmap"
      >
        {heatmapQuery.isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : heatmapQuery.isError ? (
          <p className="text-sm text-muted-foreground">{t("portfolio.sectorLoadFail")}</p>
        ) : (
          <SectorHeatmap tiles={heatmapQuery.data ?? []} />
        )}
      </SectionCard>

      {/* 하단 2열: 월간 수익률 캘린더 + AI 인사이트 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("portfolio.monthlyCalendar")}
          className="lg:col-span-8"
          testId="portfolio-section-calendar"
        >
          {calendarQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <MonthlyReturnCalendar
              cells={calendarQuery.data ?? []}
              year={new Date().getFullYear()}
            />
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
        <h2
          id="portfolio-rebalance-title"
          className="text-sm font-semibold tracking-tight"
        >
          {t("portfolio.rebalance")}
        </h2>
        <RebalancePanel />
      </section>
    </div>
  );
}
