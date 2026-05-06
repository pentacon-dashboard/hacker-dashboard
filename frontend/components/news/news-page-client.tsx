"use client";

import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState } from "@/components/common/error-state";
import { NewsPanel } from "@/components/dashboard/news-panel";
import { SectionCard } from "@/components/dashboard/section-card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPortfolioSummary } from "@/lib/api/portfolio";
import {
  buildDashboardNewsQuery,
  getDisplayableHoldingSymbols,
} from "@/lib/portfolio/display-safety";

export function NewsPageClient() {
  const searchParams = useSearchParams();
  const clientId = searchParams.get("client_id");

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary", "news", clientId],
    queryFn: () => getPortfolioSummary(30, clientId ?? undefined),
    staleTime: 30_000,
  });

  const symbols = useMemo(
    () => getDisplayableHoldingSymbols(summaryQuery.data?.holdings ?? []),
    [summaryQuery.data?.holdings],
  );
  const newsQuery = useMemo(
    () => buildDashboardNewsQuery(summaryQuery.data?.holdings ?? []),
    [summaryQuery.data?.holdings],
  );
  const displayName = summaryQuery.data?.client_name ?? clientId ?? "전체 고객";

  return (
    <div className="space-y-5" data-testid="news-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">관련 뉴스</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {displayName} 보유 종목 기준으로 뉴스와 공시를 확인합니다.
        </p>
      </div>

      <SectionCard title="보유 종목 뉴스" testId="client-news-section">
        {summaryQuery.isLoading ? (
          <div className="space-y-3" data-testid="client-news-loading">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="flex gap-3">
                <Skeleton className="h-12 w-12 shrink-0 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-11/12" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : summaryQuery.isError ? (
          <ErrorState
            title="뉴스 기준 데이터 로드 실패"
            description="선택 고객의 보유 종목을 불러오지 못했습니다."
            onRetry={() => void summaryQuery.refetch()}
          />
        ) : (
          <NewsPanel symbols={symbols} query={newsQuery} limit={8} />
        )}
      </SectionCard>
    </div>
  );
}
