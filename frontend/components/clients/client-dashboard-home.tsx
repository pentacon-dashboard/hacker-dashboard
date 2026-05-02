"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { SectionCard } from "@/components/dashboard/section-card";
import { SelectedClientDashboard } from "@/components/dashboard/dashboard-home";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getPortfolioClients,
  type PortfolioClientsResponse,
} from "@/lib/api/portfolio";
import { cn } from "@/lib/utils";
import {
  formatKRWCompact,
  formatPct,
  signedColorClass,
} from "@/lib/utils/format";

type ClientRow = PortfolioClientsResponse["clients"][number];

function riskTone(riskGrade: string) {
  if (riskGrade === "high") return "border-red-200 bg-red-50 text-red-700";
  if (riskGrade === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function riskLabel(riskGrade: string) {
  if (riskGrade === "high") return "높음";
  if (riskGrade === "medium") return "중간";
  if (riskGrade === "low") return "낮음";
  return riskGrade;
}

function ClientDashboardHomeSkeleton() {
  return (
    <div className="space-y-5" data-testid="client-dashboard-home-loading">
      <div className="space-y-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-xl border bg-card p-4 shadow-sm">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="mt-3 h-6 w-24" />
          </div>
        ))}
      </div>
      <div className="grid gap-3 xl:grid-cols-[285px_minmax(0,1fr)]">
        <Skeleton className="h-[520px] w-full" />
        <Skeleton className="h-[520px] w-full" />
      </div>
    </div>
  );
}

function ClientBookSummary({ data }: { data: PortfolioClientsResponse }) {
  const clients = data.clients;
  const highRiskCount = clients.filter((client) => client.risk_grade === "high").length;
  const averageReturnPct =
    clients.reduce((sum, client) => sum + Number(client.total_pnl_pct), 0) /
    Math.max(clients.length, 1);

  return (
    <section
      aria-label="고객장부 핵심 지표"
      className="grid grid-cols-2 gap-3 lg:grid-cols-4"
    >
      <KpiCard
        label="관리 자산"
        value={formatKRWCompact(data.aum_krw)}
        delta="전체 고객 합산"
        icon={<Wallet className="h-4 w-4" />}
        accent="blue"
        testId="client-book-total-aum"
      />
      <KpiCard
        label="고객 수"
        value={`${data.client_count}`}
        delta="활성 고객 기준"
        icon={<Users className="h-4 w-4" />}
        accent="slate"
        testId="client-book-client-count"
      />
      <KpiCard
        label="고위험 고객"
        value={`${highRiskCount}`}
        delta="위험도 '높음' 고객"
        icon={<ShieldAlert className="h-4 w-4" />}
        accent="amber"
        testId="client-book-high-risk"
      />
      <KpiCard
        label="평균 수익률"
        value={formatPct(averageReturnPct, { signed: true })}
        delta="전체 고객 평균 (30일)"
        deltaValue={averageReturnPct}
        icon={<TrendingUp className="h-4 w-4" />}
        accent={averageReturnPct >= 0 ? "green" : "rose"}
        testId="client-book-average-return"
      />
    </section>
  );
}

function ClientListPanel({
  clients,
  selectedClientId,
  query,
  onQueryChange,
  onSelect,
}: {
  clients: ClientRow[];
  selectedClientId: string;
  query: string;
  onQueryChange: (value: string) => void;
  onSelect: (clientId: string) => void;
}) {
  return (
    <SectionCard title="고객 목록" testId="client-book">
      <div className="mb-4 flex gap-2">
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">고객 검색</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="고객명 또는 ID 검색"
            className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
            data-testid="client-search-input"
          />
        </label>
        <button
          type="button"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-card text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="고객 필터"
        >
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="space-y-3">
        {clients.map((client) => {
          const active = client.client_id === selectedClientId;
          return (
            <button
              key={client.client_id}
              type="button"
              onClick={() => onSelect(client.client_id)}
              className={cn(
                "w-full rounded-md border bg-card p-3 text-left shadow-sm transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "border-primary bg-primary/5"
                  : "border-border hover:bg-muted/50",
              )}
              aria-pressed={active}
              data-testid={`client-select-${client.client_id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <BriefcaseBusiness className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <h2 className="truncate text-base font-semibold">
                      {client.client_name}
                    </h2>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {client.client_id}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${riskTone(
                    client.risk_grade,
                  )}`}
                >
                  {riskLabel(client.risk_grade)}
                </span>
              </div>

              <div className="mt-5 flex items-end justify-between gap-3">
                <div>
                  <p className="font-semibold tabular-nums">
                    {formatKRWCompact(client.aum_krw)}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {client.holdings_count} 종목
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`text-sm font-semibold tabular-nums ${signedColorClass(
                      client.total_pnl_pct,
                    )}`}
                  >
                    {formatPct(client.total_pnl_pct, { signed: true })}
                  </span>
                  <ArrowRight
                    className={cn(
                      "h-4 w-4",
                      active ? "text-primary" : "text-muted-foreground",
                    )}
                    aria-hidden="true"
                  />
                </div>
              </div>
            </button>
          );
        })}

        {clients.length === 0 ? (
          <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            검색 결과가 없습니다.
          </div>
        ) : null}
      </div>

      <Link
        href="/upload"
        className="mt-5 flex h-10 w-full items-center justify-center rounded-md border bg-card text-sm font-semibold transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        data-testid="new-client-upload-link"
      >
        + 새 고객 등록
      </Link>
    </SectionCard>
  );
}

export function ClientDashboardHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedFromUrl = searchParams.get("client") ?? "";
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [clientQuery, setClientQuery] = useState("");
  const clientsQuery = useQuery({
    queryKey: ["portfolio", "clients"],
    queryFn: getPortfolioClients,
    staleTime: 60_000,
  });

  const data = clientsQuery.data;
  const clients = useMemo(() => data?.clients ?? [], [data?.clients]);
  const filteredClients = useMemo(() => {
    const normalized = clientQuery.trim().toLowerCase();
    if (!normalized) return clients;
    return clients.filter((client) =>
      `${client.client_name} ${client.client_id}`.toLowerCase().includes(normalized),
    );
  }, [clientQuery, clients]);

  useEffect(() => {
    if (clients.length === 0) return;
    const matchedFromUrl = clients.find(
      (client) => client.client_id === selectedFromUrl,
    );
    const nextClientId = matchedFromUrl?.client_id ?? clients[0]!.client_id;
    setSelectedClientId((current) =>
      current === nextClientId ? current : nextClientId,
    );
  }, [clients, selectedFromUrl]);

  function handleSelect(clientId: string) {
    setSelectedClientId(clientId);
    router.replace(`/?client=${encodeURIComponent(clientId)}`, { scroll: false });
  }

  const selectedClient =
    clients.find((client) => client.client_id === selectedClientId) ?? clients[0] ?? null;
  const activeClientId = selectedClient?.client_id ?? "";

  if (clientsQuery.isLoading) {
    return <ClientDashboardHomeSkeleton />;
  }

  if (clientsQuery.isError) {
    return (
      <ErrorState
        title="고객장부 로드 실패"
        description="PB 고객 목록을 불러올 수 없습니다."
        onRetry={() => void clientsQuery.refetch()}
      />
    );
  }

  if (!data || clients.length === 0) {
    return (
      <EmptyState
        title="관리 중인 고객이 없습니다"
        description="고객 포트폴리오 데이터를 업로드하거나 생성하면 고객장부를 시작할 수 있습니다."
        action={
          <Link
            href="/upload"
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground"
          >
            CSV 파일 업로드
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-5" data-testid="client-dashboard-home">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">고객장부</h1>
      </div>

      <ClientBookSummary data={data} />

      <section className="grid items-start gap-3 xl:grid-cols-[285px_minmax(0,1fr)]">
        <ClientListPanel
          clients={filteredClients}
          selectedClientId={activeClientId}
          query={clientQuery}
          onQueryChange={setClientQuery}
          onSelect={handleSelect}
        />

        {selectedClient ? (
          <div className="min-w-0 rounded-xl border bg-card p-4 shadow-sm">
            <SelectedClientDashboard
              clientId={activeClientId}
              clientName={selectedClient.client_name}
              clientRiskGrade={selectedClient.risk_grade}
              variant="clientBook"
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
