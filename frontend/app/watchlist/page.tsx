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
import { Skeleton } from "@/components/ui/skeleton";
import {
  getWatchlistSummary,
  getWatchlistPopular,
  getWatchlistGainersLosers,
} from "@/lib/api/watchlist";

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
  const summaryQuery = useQuery({
    queryKey: ["watchlist", "summary"],
    queryFn: getWatchlistSummary,
    staleTime: 30_000,
  });

  const popularQuery = useQuery({
    queryKey: ["watchlist", "popular"],
    queryFn: getWatchlistPopular,
    staleTime: 60_000,
  });

  const gainersLosersQuery = useQuery({
    queryKey: ["watchlist", "gainers-losers"],
    queryFn: getWatchlistGainersLosers,
    staleTime: 60_000,
  });

  const summary = summaryQuery.data;

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">워치리스트</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          관심 종목을 추가하고 실시간 시세를 확인하세요.
        </p>
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
              label="관심종목 수"
              value={`${summary?.watched_count ?? 0}`}
              delta="종목"
              icon={<Eye className="h-4 w-4" />}
              accent="blue"
              testId="watchlist-kpi-count"
            />
            <KpiCard
              label="상승 평균"
              value={summary ? `+${Number(summary.up_avg_pct).toFixed(2)}%` : "-"}
              deltaValue={summary ? Number(summary.up_avg_pct) : undefined}
              icon={<TrendingUp className="h-4 w-4" />}
              accent="green"
              testId="watchlist-kpi-up-avg"
            />
            <KpiCard
              label="하락 평균"
              value={summary ? `${Number(summary.down_avg_pct).toFixed(2)}%` : "-"}
              deltaValue={summary ? Number(summary.down_avg_pct) : undefined}
              icon={<TrendingDown className="h-4 w-4" />}
              accent="rose"
              testId="watchlist-kpi-down-avg"
            />
            <KpiCard
              label="최고 수익률"
              value={summary?.top_gainer ?? "-"}
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
          title="워치리스트 종목"
          className="lg:col-span-8"
          testId="watchlist-section-table"
        >
          <WatchlistTable />
        </SectionCard>

        <div className="space-y-4 lg:col-span-4">
          <SectionCard
            title="인기 TOP 5"
            testId="watchlist-section-popular"
          >
            {popularQuery.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <PopularTop5
                items={popularQuery.data ?? []}
                title="인기 TOP 5"
              />
            )}
          </SectionCard>

          <SectionCard
            title="등락 TOP 5"
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
        <SectionCard title="알림 설정" testId="watchlist-section-alerts">
          <AlertSettingsCard />
        </SectionCard>

        <SectionCard title="최근 체결" testId="watchlist-section-trades">
          <RecentTradesPanel />
        </SectionCard>

        <SectionCard title="맞춤 알림 설정" testId="watchlist-section-custom-alerts">
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            Phase B-γ 연동 후 활성화
          </div>
        </SectionCard>
      </section>
    </div>
  );
}
