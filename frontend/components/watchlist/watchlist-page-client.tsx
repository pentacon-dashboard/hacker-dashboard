"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { Bell, ListChecks, SearchCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AlertSettingsCard } from "@/components/watchlist/alert-settings-card";
import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { AssetBadge } from "@/components/common/asset-badge";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionCard } from "@/components/dashboard/section-card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getPortfolioSummary,
  type HoldingDetail,
} from "@/lib/api/portfolio";
import { getDisplayableHoldings } from "@/lib/portfolio/display-safety";
import { getSymbolDisplayParts } from "@/lib/market/display";
import { cn } from "@/lib/utils";
import { formatKRWCompact, formatPct } from "@/lib/utils/format";

function watchlistHref(
  clientId: string | null,
  params: Record<string, string>,
): string {
  const search = new URLSearchParams();
  if (clientId) search.set("client_id", clientId);
  Object.entries(params).forEach(([key, value]) => search.set(key, value));
  const qs = search.toString();
  return `/watchlist${qs ? `?${qs}` : ""}`;
}

function assetClassForMarket(market: string): string {
  if (market === "upbit" || market === "binance") return "crypto";
  if (market === "naver_kr" || market === "krx" || market === "kiwoom") return "stock";
  if (market === "yahoo") return "stock";
  return "macro";
}

function attentionReasons(holding: HoldingDetail, totalValue: number): string[] {
  const reasons: string[] = [];
  const pnlPct = Number(holding.pnl_pct);
  const valueKrw = Number(holding.value_krw);
  const share = totalValue > 0 ? valueKrw / totalValue : 0;

  if (Number.isFinite(pnlPct) && pnlPct < 0) {
    reasons.push(`손실 ${formatPct(pnlPct, { signed: true })}`);
  }
  if (share >= 0.2) {
    reasons.push(`집중도 ${(share * 100).toFixed(1)}%`);
  }

  return reasons;
}

function AttentionHoldingsPanel({ clientId }: { clientId: string | null }) {
  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary", "attention", clientId],
    queryFn: () => getPortfolioSummary(30, clientId ?? undefined),
    staleTime: 30_000,
  });

  const attentionRows = useMemo(() => {
    const summary = summaryQuery.data;
    if (!summary) return [];
    const totalValue = Number(summary.total_value_krw);
    return getDisplayableHoldings(summary.holdings)
      .map((holding) => ({
        holding,
        reasons: attentionReasons(holding, totalValue),
        valueShare:
          totalValue > 0 ? Number(holding.value_krw) / totalValue : 0,
      }))
      .filter((row) => row.reasons.length > 0)
      .sort((a, b) => b.valueShare - a.valueShare || Number(a.holding.pnl_pct) - Number(b.holding.pnl_pct));
  }, [summaryQuery.data]);

  if (summaryQuery.isLoading) {
    return (
      <div className="space-y-2" data-testid="attention-holdings-loading">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (summaryQuery.isError) {
    return (
      <ErrorState
        title="주의 종목 로드 실패"
        description="선택 고객의 보유 종목을 불러오지 못했습니다."
        onRetry={() => void summaryQuery.refetch()}
      />
    );
  }

  if (attentionRows.length === 0) {
    return (
      <EmptyState
        title="주의 종목 없음"
        description="손실 구간이거나 포트폴리오 비중이 큰 보유 종목이 없습니다."
      />
    );
  }

  return (
    <ul className="space-y-2" data-testid="attention-holdings-panel">
      {attentionRows.map(({ holding, reasons }) => {
        const displayParts = getSymbolDisplayParts(holding.market, holding.code);
        return (
          <li
            key={`${holding.market}:${holding.code}`}
            className="flex items-center justify-between gap-3 rounded-md border p-3"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Link
                  href={`/symbol/${encodeURIComponent(holding.market)}/${encodeURIComponent(holding.code)}`}
                  className="truncate text-sm font-semibold hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {displayParts.primary}
                </Link>
                <AssetBadge assetClass={assetClassForMarket(holding.market)} />
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {displayParts.secondary ?? holding.code}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-sm font-semibold tabular-nums">
                {formatKRWCompact(holding.value_krw)}
              </p>
              <p className="text-xs text-muted-foreground">{reasons.join(" · ")}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex h-9 items-center rounded-md border px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "border-primary bg-primary/10 text-primary"
          : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      {children}
    </Link>
  );
}

export function WatchlistPageClient() {
  const searchParams = useSearchParams();
  const clientId = searchParams.get("client_id");
  const activeTab = searchParams.get("tab") === "alerts" ? "alerts" : "watchlist";
  const activeFilter = searchParams.get("filter");
  const showAttention = activeFilter === "attention";
  const showAlertsFirst = activeTab === "alerts";

  return (
    <div className="space-y-5" data-testid="watchlist-page">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">관심 종목</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {clientId
              ? `${clientId} 기준 모니터링, 가격 알림, 주의 종목을 확인합니다.`
              : "관심 종목과 가격 알림을 관리합니다."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <NavLink
            href={watchlistHref(clientId, {})}
            active={!showAttention && !showAlertsFirst}
          >
            <ListChecks className="mr-1.5 h-4 w-4" aria-hidden="true" />
            관심 종목
          </NavLink>
          <NavLink
            href={watchlistHref(clientId, { filter: "attention" })}
            active={showAttention}
          >
            <SearchCheck className="mr-1.5 h-4 w-4" aria-hidden="true" />
            주의 종목
          </NavLink>
          <NavLink
            href={watchlistHref(clientId, { tab: "alerts" })}
            active={showAlertsFirst}
          >
            <Bell className="mr-1.5 h-4 w-4" aria-hidden="true" />
            가격 알림
          </NavLink>
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        {showAlertsFirst ? (
          <SectionCard title="가격 알림" testId="watchlist-alerts-section">
            <AlertSettingsCard />
          </SectionCard>
        ) : showAttention ? (
          <SectionCard title="주의 종목" testId="watchlist-attention-section">
            <AttentionHoldingsPanel clientId={clientId} />
          </SectionCard>
        ) : (
          <SectionCard title="관심 종목" testId="watchlist-items-section">
            <WatchlistTable />
          </SectionCard>
        )}

        <SectionCard
          title={showAlertsFirst ? "관심 종목" : "가격 알림"}
          testId={showAlertsFirst ? "watchlist-items-side-section" : "watchlist-alerts-side-section"}
        >
          {showAlertsFirst ? <WatchlistTable /> : <AlertSettingsCard />}
        </SectionCard>
      </section>
    </div>
  );
}
