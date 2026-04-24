"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Wallet,
  TrendingUp,
  LineChart as LineChartIcon,
  Layers,
  BadgeDollarSign,
  AlertTriangle,
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
import {
  getPortfolioSummary,
  getSnapshots,
  type PortfolioSummary,
  type SnapshotResponse,
} from "@/lib/api/portfolio";
import {
  formatKRWCompact,
  formatPct,
  signedColorClass,
} from "@/lib/utils/format";

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "국내 주식",
  stock_us: "해외 주식",
  crypto: "암호화폐",
  cash: "현금",
  fx: "외환",
  other: "기타",
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
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<PeriodKey>("1M");
  const { t } = useLocale();

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setSummary(null);
    setSnapshots(null);

    const days = PERIOD_DAYS[period];
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - days);
    const fromStr = formatDate(from);
    const toStr = formatDate(to);

    Promise.all([
      getPortfolioSummary(days),
      getSnapshots(fromStr, toStr).catch(() => [] as SnapshotResponse[]),
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

    return () => {
      cancelled = true;
    };
  }, [period]);

  const allocationSlices = useMemo<AllocationSlice[]>(() => {
    if (!summary) return [];
    const total = Number(summary.total_value_krw);
    return Object.entries(summary.asset_class_breakdown)
      .map(([key, ratio]) => {
        const r = Number(ratio);
        return {
          key,
          name: ASSET_CLASS_LABELS[key] ?? key,
          ratio: r,
          value_krw: Number.isFinite(total) ? total * r : 0,
          color: ASSET_CLASS_COLORS[key] ?? "#94a3b8",
        };
      })
      .sort((a, b) => b.ratio - a.ratio);
  }, [summary]);

  // 오늘 손익: daily_change_krw / daily_change_pct 재사용
  const todayPnlKrw = summary ? summary.daily_change_krw : "0";
  const todayPnlPct = summary ? summary.daily_change_pct : "0";

  const dateRange = useMemo(() => {
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - PERIOD_DAYS[period]);
    return `${formatDate(from)} ~ ${formatDate(to)}`;
  }, [period]);

  const hasError = error !== null;
  const isLoading = summary === null;

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
              label="총자산"
              value={formatKRWCompact(summary.total_value_krw)}
              delta={formatPct(summary.total_pnl_pct, { signed: true })}
              deltaValue={Number(summary.total_pnl_pct)}
              icon={<Wallet className="h-4 w-4" />}
              accent="blue"
              testId="kpi-total-value"
            />
            <KpiCard
              label="일간 변동"
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
              label={`${summary.period_days}일 변동`}
              value={formatPct(summary.period_change_pct, { signed: true })}
              deltaValue={Number(summary.period_change_pct)}
              icon={<LineChartIcon className="h-4 w-4" />}
              accent="violet"
              testId="kpi-period-change"
            />
            <KpiCard
              label="보유 종목"
              value={`${summary.holdings_count}`}
              delta="종목"
              icon={<Layers className="h-4 w-4" />}
              accent="slate"
              testId="kpi-holdings-count"
            />
            {/* KPI 5번째: 오늘 손익 (목업 교체) */}
            <KpiCard
              label="오늘 손익"
              value={formatKRWCompact(todayPnlKrw)}
              delta={formatPct(todayPnlPct, { signed: true })}
              deltaValue={Number(todayPnlPct)}
              icon={<BadgeDollarSign className="h-4 w-4" />}
              accent="rose"
              testId="kpi-today-pnl"
            />
            <KpiCard
              label="집중도 리스크"
              value={formatPct(summary.risk_score_pct)}
              delta={
                Number(summary.risk_score_pct) >= 66
                  ? "높음"
                  : Number(summary.risk_score_pct) >= 33
                    ? "보통"
                    : "양호"
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
          title="자산 가치 추이"
          className="lg:col-span-5"
          testId="section-networth"
          action={
            <span className="text-xs text-muted-foreground">
              최근 {PERIOD_DAYS[period]}일
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
          title="자산 배분"
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
          title="집중도 리스크"
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
          title="보유 자산 TOP 5"
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
            <TopHoldingsTable
              holdings={summary.holdings}
              limit={5}
              totalValueKrw={Number(summary.total_value_krw)}
              showAvgCost
              showCurrentPrice
            />
          )}
        </SectionCard>

        <SectionCard
          title="디멘션 분석 (섹터별 수익률)"
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
          title="시장 주도주"
          className="lg:col-span-3"
          testId="section-market-leaders"
        >
          <MarketLeaders limit={5} />
        </SectionCard>
      </section>

      {/* 최신 뉴스 섹션 */}
      <section data-testid="section-news">
        <SectionCard
          title="최신 뉴스"
          testId="section-news-card"
          action={
            <span className="text-xs text-muted-foreground">보유 종목 연관 기사</span>
          }
        >
          <NewsPanel
            symbols={summary?.holdings.map((h) => h.code) ?? []}
            query={(() => {
              if (!summary) return undefined;
              const codes = summary.holdings.map((h) => h.code);
              return codes.length > 0 ? codes.slice(0, 5).join(" OR ") : "market";
            })()}
            limit={5}
          />
        </SectionCard>
      </section>
    </div>
  );
}
