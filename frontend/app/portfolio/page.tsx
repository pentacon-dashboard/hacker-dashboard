"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Wallet, TrendingUp, BarChart3, Layers, Target, Users } from "lucide-react";
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
import { ClientBriefingDialog } from "@/components/reports/client-briefing-dialog";
import { useLocale } from "@/lib/i18n/locale-provider";
import { useDataSettings } from "@/lib/hooks/use-data-settings";
import {
  getPortfolioSummary,
  getPortfolioClients,
  getSectorHeatmap,
  getMonthlyReturns,
  getAiInsight,
  type PortfolioClientsResponse,
} from "@/lib/api/portfolio";
import {
  formatKRWCompact,
  formatPct,
  formatSignedNumber,
  signedColorClass,
} from "@/lib/utils/format";
import { getDisplayableHoldings } from "@/lib/portfolio/display-safety";

export const dynamic = "force-dynamic";

export default function PortfolioPage() {
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();
  const [selectedClientId, setSelectedClientId] = useState("client-001");
  const currentYear = new Date().getFullYear();

  const clientsQuery = useQuery({
    queryKey: ["portfolio", "clients"],
    queryFn: getPortfolioClients,
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary", selectedClientId],
    queryFn: () => getPortfolioSummary(undefined, selectedClientId),
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const heatmapQuery = useQuery({
    queryKey: ["portfolio", "sectors", "heatmap", selectedClientId],
    queryFn: () => getSectorHeatmap(selectedClientId),
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const calendarQuery = useQuery({
    queryKey: ["portfolio", "monthly-returns", currentYear, selectedClientId],
    queryFn: () => getMonthlyReturns(currentYear, selectedClientId),
    staleTime: 300_000,
  });

  const insightQuery = useQuery({
    queryKey: ["portfolio", "ai-insight", selectedClientId],
    queryFn: () => getAiInsight(selectedClientId),
    staleTime: 300_000,
  });

  useEffect(() => {
    const clients = clientsQuery.data?.clients ?? [];
    if (clients.length === 0) return;
    const hasSelectedClient = clients.some((client) => client.client_id === selectedClientId);
    if (!hasSelectedClient) {
      setSelectedClientId(clients[0]!.client_id);
    }
  }, [clientsQuery.data, selectedClientId]);

  const isLoading = summaryQuery.isLoading;
  const isError = summaryQuery.isError;
  const clientRows = clientsQuery.data?.clients ?? [];
  const selectedClient = clientRows.find((client) => client.client_id === selectedClientId);
  const clientName = selectedClient?.client_name ?? selectedClientId;
  const summary = summaryQuery.data;
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

  function renderClientBook(data?: PortfolioClientsResponse | null) {
    const rows = data?.clients ?? [];
    return (
      <SectionCard
        title="PB 고객 목록"
        testId="portfolio-section-clients"
        action={
          data ? (
            <span className="text-xs text-muted-foreground">
              전체 AUM {formatKRWCompact(data.aum_krw)}
            </span>
          ) : null
        }
      >
        {clientsQuery.isLoading ? (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
            등록된 고객 포트폴리오가 없습니다.
          </div>
        ) : (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {rows.map((client) => {
              const active = client.client_id === selectedClientId;
              return (
                <button
                  key={client.client_id}
                  type="button"
                  onClick={() => setSelectedClientId(client.client_id)}
                  className={`min-h-24 rounded-md border p-3 text-left transition-colors ${
                    active
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-accent"
                  }`}
                  aria-pressed={active}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2 text-sm font-semibold">
                      <Users className="h-4 w-4 shrink-0" />
                      <span className="truncate">{client.client_name}</span>
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        client.risk_grade === "high"
                          ? "bg-red-100 text-red-700"
                          : client.risk_grade === "medium"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {client.risk_grade}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <p className="text-muted-foreground">AUM</p>
                      <p className="mt-1 font-semibold tabular-nums">
                        {formatKRWCompact(client.aum_krw)}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">보유</p>
                      <p className="mt-1 font-semibold tabular-nums">
                        {client.holdings_count}개
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">손익률</p>
                      <p
                        className={`mt-1 font-semibold tabular-nums ${signedColorClass(client.total_pnl_pct)}`}
                      >
                        {formatPct(client.total_pnl_pct, { signed: true })}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </SectionCard>
    );
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

  if (!summary || summary.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
            <p className="text-sm text-muted-foreground">
              {clientName} 고객의 PB 워크스테이션
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ClientBriefingDialog
              clientId={selectedClientId}
              clientName={selectedClient?.client_name}
            />
            <AddHoldingDialog clientId={selectedClientId} />
          </div>
        </div>
        {renderClientBook(clientsQuery.data)}
        <EmptyState
          title={t("portfolio.emptyTitle")}
          description={t("portfolio.emptyDesc")}
          action={<AddHoldingDialog clientId={selectedClientId} />}
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
  const hasOnlyCorruptedHoldings =
    summary.holdings.length > 0 && displayHoldings.length === 0;

  if (hasOnlyCorruptedHoldings) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
            <p className="text-sm text-muted-foreground">
              {clientName} 고객의 PB 워크스테이션
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ClientBriefingDialog
              clientId={selectedClientId}
              clientName={selectedClient?.client_name}
            />
            <AddHoldingDialog clientId={selectedClientId} />
          </div>
        </div>

        {renderClientBook(clientsQuery.data)}

        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">{t("common.dataCorruptedTitle")}</p>
          <p className="mt-1 text-xs text-amber-800">
            보유 종목 {hiddenHoldingCount}건은 심볼 또는 통화 값이 손상되어 포트폴리오 요약에서 제외했습니다.
          </p>
        </div>

        <EmptyState
          title="표시 가능한 보유 종목이 없습니다"
          description="손상된 데이터를 숨겼습니다. 보유 종목을 다시 등록하면 포트폴리오 분석이 정상적으로 표시됩니다."
          action={<AddHoldingDialog clientId={selectedClientId} />}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("portfolio.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {clientName} 고객의 PB 워크스테이션
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ClientBriefingDialog
            clientId={selectedClientId}
            clientName={selectedClient?.client_name}
          />
          <AddHoldingDialog clientId={selectedClientId} />
        </div>
      </div>

      {renderClientBook(clientsQuery.data)}

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
          {hiddenHoldingCount > 0 && (
            <p className="mb-3 text-xs text-muted-foreground">
              일부 보유 종목은 심볼 또는 통화 데이터가 올바르지 않아 숨김 처리되었습니다.
            </p>
          )}
          <HoldingsTable holdings={displayHoldings} />
        </SectionCard>
      </section>

      {/* 하단: 섹터 히트맵 */}
      <SectionCard
        title="GICS 섹터 트리맵"
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
              year={currentYear}
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
        <RebalancePanel clientId={selectedClientId} />
      </section>
    </div>
  );
}
