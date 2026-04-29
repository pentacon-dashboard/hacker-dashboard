"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Wallet,
  TrendingUp,
  LineChart as LineChartIcon,
  Layers,
  BadgeDollarSign,
  AlertTriangle,
  Users,
} from "lucide-react";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { RiskGauge } from "@/components/dashboard/risk-gauge";
import { DimensionBars } from "@/components/dashboard/dimension-bars";
import { TopHoldingsTable } from "@/components/dashboard/top-holdings-table";
import { SectionCard } from "@/components/dashboard/section-card";
import {
  AllocationBreakdown,
  type AllocationSlice,
} from "@/components/dashboard/allocation-breakdown";
import {
  PeriodTabs,
  PERIOD_DAYS,
  type PeriodKey,
} from "@/components/dashboard/period-tabs";
import { MarketLeaders } from "@/components/dashboard/market-leaders";
import { NetworthChart } from "@/components/portfolio/networth-chart";
import { NewsPanel } from "@/components/dashboard/news-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocale } from "@/lib/i18n/locale-provider";
import { useDataSettings } from "@/lib/hooks/use-data-settings";
import {
  getPortfolioSummary,
  getPortfolioClients,
  getSnapshots,
  type PortfolioClientsResponse,
  type PortfolioSummary,
  type SnapshotResponse,
} from "@/lib/api/portfolio";
import {
  formatKRWCompact,
  formatPct,
  signedColorClass,
} from "@/lib/utils/format";
import {
  buildDashboardNewsQuery,
  getDisplayableHoldings,
  getDisplayableHoldingSymbols,
} from "@/lib/portfolio/display-safety";

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

function formatDate(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export default function DashboardHome() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotResponse[] | null>(null);
  const [clients, setClients] = useState<PortfolioClientsResponse | null>(null);
  const [selectedClientId, setSelectedClientId] = useState("client-001");
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<PeriodKey>("1M");
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();

  // Stable ref to the fetch function so the interval can always call the latest version
  const fetchRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPortfolioClients()
      .then((data) => {
        if (cancelled) return;
        setClients(data);
        const firstClient = data.clients[0]?.client_id;
        if (firstClient) setSelectedClientId(firstClient);
      })
      .catch(() => {
        if (!cancelled) setClients(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setSummary(null);
    setSnapshots(null);

    const days = PERIOD_DAYS[period];

    function doFetch() {
      const to = new Date();
      const from = new Date();
      from.setDate(to.getDate() - days);
      const fromStr = formatDate(from);
      const toStr = formatDate(to);

      Promise.all([
        getPortfolioSummary(days, selectedClientId),
        getSnapshots(fromStr, toStr, selectedClientId).catch(() => [] as SnapshotResponse[]),
      ])
        .then(([s, snaps]) => {
          if (cancelled) return;
          setSummary(s);
          setSnapshots(snaps);
        })
        .catch((err) => {
          if (!cancelled) {
            setError(
              err instanceof Error ? err.message : "대시보드 데이터 로드 실패",
            );
          }
        });
    }

    fetchRef.current = doFetch;
    doFetch();

    return () => {
      cancelled = true;
    };
  }, [period, selectedClientId]);

  // Auto-refresh interval — responds to settings changes without re-fetching from scratch
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      fetchRef.current?.();
    }, refreshIntervalMs);
    return () => clearInterval(id);
  }, [autoRefresh, refreshIntervalMs]);

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
          color: ASSET_CLASS_COLORS[key] ?? "#94a3b8",
        };
      })
      .sort((a, b) => b.ratio - a.ratio);
  }, [summary, t]);

  // 오늘 손익: daily_change_krw / daily_change_pct 재사용
  const todayPnlKrw = summary ? summary.daily_change_krw : "0";
  const todayPnlPct = summary ? summary.daily_change_pct : "0";

  const dateRange = useMemo(() => {
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - PERIOD_DAYS[period]);
    return `${formatDate(from)} ~ ${formatDate(to)}`;
  }, [period]);
  const displayHoldings = useMemo(
    () => getDisplayableHoldings(summary?.holdings ?? []),
    [summary],
  );
  const hiddenHoldingCount = Math.max(
    0,
    (summary?.holdings.length ?? 0) - displayHoldings.length,
  );
  const newsSymbols = useMemo(
    () => getDisplayableHoldingSymbols(summary?.holdings ?? []),
    [summary],
  );
  const newsQuery = useMemo(
    () => buildDashboardNewsQuery(summary?.holdings ?? []),
    [summary],
  );

  const hasError = error !== null;
  const isLoading = summary === null;
  const selectedClient = clients?.clients.find(
    (client) => client.client_id === selectedClientId,
  );
  const hasOnlyCorruptedHoldings =
    summary !== null && hiddenHoldingCount > 0 && displayHoldings.length === 0;

  function renderClientBook() {
    return (
      <SectionCard
        title="PB 고객 북"
        testId="section-client-book"
        action={
          clients ? (
            <span className="text-xs text-muted-foreground">
              전체 AUM {formatKRWCompact(clients.aum_krw)}
            </span>
          ) : null
        }
      >
        {clients === null ? (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : clients.clients.length === 0 ? (
          <div className="flex h-20 items-center justify-center text-sm text-muted-foreground">
            등록된 고객 포트폴리오가 없습니다.
          </div>
        ) : (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {clients.clients.map((client) => {
              const active = client.client_id === selectedClientId;
              return (
                <button
                  key={client.client_id}
                  type="button"
                  onClick={() => setSelectedClientId(client.client_id)}
                  className={`min-h-20 rounded-md border p-3 text-left transition-colors ${
                    active ? "border-primary bg-primary/5" : "border-border hover:bg-accent"
                  }`}
                  aria-pressed={active}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2 text-sm font-semibold">
                      <Users className="h-4 w-4 shrink-0" />
                      <span className="truncate">{client.client_name}</span>
                    </span>
                    <span
                      className={`text-xs font-semibold ${signedColorClass(client.total_pnl_pct)}`}
                    >
                      {formatPct(client.total_pnl_pct, { signed: true })}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>{formatKRWCompact(client.aum_krw)}</span>
                    <span>{client.holdings_count}개 보유</span>
                    <span>{client.risk_grade}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
        {selectedClient && (
          <p className="mt-3 text-xs text-muted-foreground">
            선택 고객: {selectedClient.client_name} ({selectedClient.client_id})
          </p>
        )}
      </SectionCard>
    );
  }

  if (hasOnlyCorruptedHoldings) {
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("dashboard.title")}</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {t("dashboard.subtitle")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <PeriodTabs value={period} onChange={setPeriod} />
            <span
              className="rounded-md border bg-card px-3 py-1 text-xs text-muted-foreground tabular-nums"
              data-testid="dashboard-date-range"
            >
              {dateRange}
            </span>
          </div>
        </div>

        {hasError && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {renderClientBook()}

        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">{t("common.dataCorruptedTitle")}</p>
          <p className="mt-1 text-xs text-amber-800">
            보유 종목 {hiddenHoldingCount}건은 심볼 또는 통화 값이 손상되어 대시보드 요약에서 제외했습니다.
          </p>
        </div>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-8">
          <SectionCard
            title={t("dashboard.latestNews")}
            className="lg:col-span-5"
            testId="section-news-card"
            action={
              <span className="text-xs text-muted-foreground">
                {t("common.marketNewsFallback")}
              </span>
            }
          >
            <NewsPanel symbols={[]} limit={5} />
          </SectionCard>
          <SectionCard
            title={t("dashboard.marketLeaders")}
            className="lg:col-span-3"
            testId="section-market-leaders"
          >
            <MarketLeaders limit={5} />
          </SectionCard>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 상단 타이틀 + 기간 탭 + 날짜 범위 */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("dashboard.title")}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {t("dashboard.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodTabs value={period} onChange={setPeriod} />
          <span
            className="rounded-md border bg-card px-3 py-1 text-xs text-muted-foreground tabular-nums"
            data-testid="dashboard-date-range"
          >
            {dateRange}
          </span>
        </div>
      </div>

      {hasError && (
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </div>
      )}

      {renderClientBook()}

      {/* KPI 스트립 — 5번째: 오늘 손익 */}
      <section aria-label="핵심 지표" className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border bg-card p-4 shadow-sm">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-3 h-6 w-24" />
            </div>
          ))
        ) : summary ? (
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
              delta={(() => {
                const krw = Number(summary.daily_change_krw);
                const compact = formatKRWCompact(krw);
                return krw > 0 ? `+${compact}` : compact;
              })()}
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
            {/* KPI 5번째: 오늘 손익 (목업 교체) */}
            <KpiCard
              label={t("dashboard.kpi.todayPnl")}
              value={formatKRWCompact(todayPnlKrw)}
              delta={formatPct(todayPnlPct, { signed: true })}
              deltaValue={Number(todayPnlPct)}
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
        ) : null}
      </section>

      {/* 중단 그리드: 목업 기준 좌-우 재배치
          왼쪽(큰) = 자산 가치 추이 라인차트
          가운데 = AllocationBreakdown (도넛 + 3컬럼)
          우측 = 집중도 게이지 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("dashboard.assetTrend")}
          className="lg:col-span-5"
          testId="section-networth"
          action={
            <span className="text-xs text-muted-foreground">
              {t("dashboard.last30Days").replace("30", String(PERIOD_DAYS[period]))}
            </span>
          }
        >
          {snapshots === null ? (
            <Skeleton className="h-56 w-full" />
          ) : (
            <NetworthChart snapshots={snapshots} />
          )}
        </SectionCard>

        <SectionCard
          title={t("dashboard.allocation")}
          className="lg:col-span-4"
          testId="section-allocation"
          action={
            summary ? (
              <span className={`text-xs font-semibold ${signedColorClass(Number(summary.total_pnl_pct))}`}>
                {formatPct(summary.total_pnl_pct, { signed: true })}
              </span>
            ) : null
          }
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

      {/* 하단 그리드: 보유 자산 TOP 5 (7컬럼) / 디멘션 분석(섹터) / 시장 주도주 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("dashboard.top5Holdings")}
          className="lg:col-span-4"
          testId="section-top-holdings"
        >
          {isLoading || !summary ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
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

      {/* 최신 뉴스 섹션 */}
      <section data-testid="section-news">
        <SectionCard
          title={t("dashboard.latestNews")}
          testId="section-news-card"
          action={
            <span className="text-xs text-muted-foreground">보유 종목 연관 기사</span>
          }
        >
          <NewsPanel
            symbols={newsSymbols}
            query={newsQuery ?? "market"}
            limit={5}
          />
        </SectionCard>
      </section>
    </div>
  );
}
