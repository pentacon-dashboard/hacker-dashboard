"use client";

import { useQuery } from "@tanstack/react-query";
import { Eye, TrendingUp, TrendingDown, Star } from "lucide-react";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SectionCard } from "@/components/dashboard/section-card";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { PopularTop5 } from "@/components/watchlist/popular-top5";
import { GainersLosersTop5 } from "@/components/watchlist/gainers-losers-top5";
import { AlertSettingsCard } from "@/components/watchlist/alert-settings-card";
import { RecentTradesPanel } from "@/components/watchlist/recent-trades-panel";
import { CustomAlertCard } from "@/components/watchlist/custom-alert-card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getWatchlistSummary,
  getWatchlistPopular,
  getWatchlistGainersLosers,
} from "@/lib/api/watchlist";
import { useLocale } from "@/lib/i18n/locale-provider";
import { useDataSettings } from "@/lib/hooks/use-data-settings";

export const dynamic = "force-dynamic";

function KpiSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-6 w-24" />
    </div>
  );
}

export default function WatchlistPage() {
  const { t } = useLocale();
  const { refreshIntervalMs, autoRefresh } = useDataSettings();

  const summaryQuery = useQuery({
    queryKey: ["watchlist", "summary"],
    queryFn: getWatchlistSummary,
    staleTime: 30_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const popularQuery = useQuery({
    queryKey: ["watchlist", "popular"],
    queryFn: getWatchlistPopular,
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const gainersLosersQuery = useQuery({
    queryKey: ["watchlist", "gainers-losers"],
    queryFn: getWatchlistGainersLosers,
    staleTime: 60_000,
    refetchInterval: autoRefresh ? refreshIntervalMs : false,
  });

  const summary = summaryQuery.data;

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("watchlist.title")}</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">{t("watchlist.subtitle")}</p>
      </div>

      {/* KPI 4개 */}
      <section
        aria-label="워치리스트 핵심 지표"
        className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      >
        {summaryQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)
        ) : (
          <>
            <KpiCard
              label={t("watchlist.kpi.count")}
              value={`${summary?.watched_count ?? 0}`}
              delta={t("table.symbol")}
              icon={<Eye className="h-4 w-4" />}
              accent="blue"
              testId="watchlist-kpi-count"
            />
            <KpiCard
              label={t("watchlist.kpi.upAvg")}
              value={summary ? `+${Number(summary.up_avg_pct).toFixed(2)}%` : "-"}
              deltaValue={summary ? Number(summary.up_avg_pct) : undefined}
              icon={<TrendingUp className="h-4 w-4" />}
              accent="green"
              testId="watchlist-kpi-up-avg"
            />
            <KpiCard
              label={t("watchlist.kpi.downAvg")}
              value={summary ? `${Number(summary.down_avg_pct).toFixed(2)}%` : "-"}
              deltaValue={summary ? Number(summary.down_avg_pct) : undefined}
              icon={<TrendingDown className="h-4 w-4" />}
              accent="rose"
              testId="watchlist-kpi-down-avg"
            />
            <KpiCard
              label={t("watchlist.kpi.topGainer")}
              value={summary?.top_gainer_name ?? t("watchlist.kpi.topGainerEmpty")}
              delta={summary?.top_gainer_pct}
              deltaValue={summary ? Number(summary.top_gainer_pct) : undefined}
              icon={<Star className="h-4 w-4" />}
              accent="amber"
              testId="watchlist-kpi-top-gainer"
            />
          </>
        )}
      </section>

      {/* 중단: 워치리스트 테이블 + 사이드 패널 */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SectionCard
          title={t("watchlist.table.title")}
          className="lg:col-span-8"
          testId="watchlist-section-table"
        >
          <WatchlistTable />
        </SectionCard>

        <div className="space-y-4 lg:col-span-4">
          <SectionCard
            title={t("watchlist.popularTop5")}
            testId="watchlist-section-popular"
          >
            {popularQuery.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <PopularTop5
                items={popularQuery.data ?? []}
                title={t("watchlist.popularTop5")}
              />
            )}
          </SectionCard>

          <SectionCard
            title={t("watchlist.gainersLosers")}
            testId="watchlist-section-gainers-losers"
          >
            {gainersLosersQuery.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <GainersLosersTop5
                gainers={gainersLosersQuery.data?.gainers ?? []}
                losers={gainersLosersQuery.data?.losers ?? []}
              />
            )}
          </SectionCard>
        </div>
      </section>

      {/* 하단: 알림 설정 + 최근 체결 */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SectionCard title={t("watchlist.alertSettings")} testId="watchlist-section-alerts">
          <AlertSettingsCard />
        </SectionCard>

        <SectionCard title={t("watchlist.recentTrades")} testId="watchlist-section-trades">
          <RecentTradesPanel />
        </SectionCard>

        <SectionCard title={t("watchlist.customAlert")} testId="watchlist-section-custom-alerts">
          <CustomAlertCard />
        </SectionCard>
      </section>
    </div>
  );
}
