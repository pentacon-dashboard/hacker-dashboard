"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AddHoldingDialog } from "@/components/portfolio/add-holding-dialog";
import { AssetPieChart } from "@/components/portfolio/asset-pie-chart";
import { NetworthChart } from "@/components/portfolio/networth-chart";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { RebalancePanel } from "@/components/portfolio/rebalance-panel";
import {
  getPortfolioSummary,
  getSnapshots,
} from "@/lib/api/portfolio";
import { formatKRW, formatPct, formatSignedNumber, signedColorClass } from "@/lib/utils/format";

export const dynamic = "force-dynamic";

/** 1개월 전 날짜를 YYYY-MM-DD 형식으로 반환 */
function oneMonthAgo(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 10);
}

function SummaryCardsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {[...Array(3)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <Skeleton className="h-4 w-24" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ChartsSkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {[...Array(2)].map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-4 w-28" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-56 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}

export default function PortfolioPage() {
  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: () => getPortfolioSummary(),
    staleTime: 30_000,
  });

  const snapshotsQuery = useQuery({
    queryKey: ["portfolio", "snapshots"],
    queryFn: () => getSnapshots(oneMonthAgo()),
    staleTime: 60_000,
  });

  const isLoading = summaryQuery.isLoading || snapshotsQuery.isLoading;
  const isError = summaryQuery.isError || snapshotsQuery.isError;

  function handleRetry() {
    void summaryQuery.refetch();
    void snapshotsQuery.refetch();
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">포트폴리오</h1>
          <p className="text-sm text-muted-foreground">자산군별 보유 현황 및 분석</p>
        </div>
        <SummaryCardsSkeleton />
        <ChartsSkeleton />
        <TableSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">포트폴리오</h1>
        </div>
        <ErrorState
          title="포트폴리오 로드 실패"
          description="데이터를 불러오는 중 문제가 생겼습니다."
          onRetry={handleRetry}
        />
      </div>
    );
  }

  const summary = summaryQuery.data;
  const snapshots = snapshotsQuery.data ?? [];

  // 보유 종목이 없는 빈 상태
  if (!summary || summary.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">포트폴리오</h1>
            <p className="text-sm text-muted-foreground">자산군별 보유 현황 및 분석</p>
          </div>
          <AddHoldingDialog />
        </div>
        <EmptyState
          title="보유자산이 없습니다"
          description="보유자산을 추가하면 포트폴리오 분석이 시작됩니다."
          action={<AddHoldingDialog />}
        />
      </div>
    );
  }

  const totalPnlColor = signedColorClass(summary.total_pnl_krw);
  const dailyChangeColor = signedColorClass(summary.daily_change_krw);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">포트폴리오</h1>
          <p className="text-sm text-muted-foreground">자산군별 보유 현황 및 분석</p>
        </div>
        <AddHoldingDialog />
      </div>

      {/* 요약 카드 3개 */}
      <div className="grid gap-4 sm:grid-cols-3">
        {/* 총자산 */}
        <Card data-testid="summary-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              총 자산
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatKRW(summary.total_value_krw)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">KRW 환산</p>
          </CardContent>
        </Card>

        {/* 총 평가손익 */}
        <Card data-testid="summary-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              총 평가손익
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold tabular-nums ${totalPnlColor}`}>
              {formatSignedNumber(summary.total_pnl_krw)}
            </div>
            <p className={`text-xs mt-1 ${totalPnlColor}`}>
              {formatPct(summary.total_pnl_pct, { signed: true })}
            </p>
          </CardContent>
        </Card>

        {/* 일간 변동 */}
        <Card data-testid="summary-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              일간 변동
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold tabular-nums ${dailyChangeColor}`}>
              {formatSignedNumber(summary.daily_change_krw)}
            </div>
            <p className={`text-xs mt-1 ${dailyChangeColor}`}>
              {formatPct(summary.daily_change_pct, { signed: true })}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 차트 2열 그리드 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">자산군 비중</CardTitle>
          </CardHeader>
          <CardContent>
            <AssetPieChart breakdown={summary.asset_class_breakdown} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">순자산 추이 (1개월)</CardTitle>
          </CardHeader>
          <CardContent>
            <NetworthChart snapshots={snapshots} />
          </CardContent>
        </Card>
      </div>

      {/* 종목별 손익 테이블 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">종목별 손익</CardTitle>
        </CardHeader>
        <CardContent>
          <HoldingsTable holdings={summary.holdings} />
        </CardContent>
      </Card>

      {/* 리밸런싱 제안 섹션 */}
      <section aria-labelledby="rebalance-heading">
        <div className="mb-4">
          <h2
            id="rebalance-heading"
            className="text-xl font-bold tracking-tight"
          >
            리밸런싱 제안
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            목표 자산 비중을 설정하면 에이전트가 구체적인 매매 액션을 제안합니다.
          </p>
        </div>
        <RebalancePanel />
      </section>
    </div>
  );
}
