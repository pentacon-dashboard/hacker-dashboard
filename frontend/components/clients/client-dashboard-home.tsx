"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  ShieldAlert,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
    <div className="space-y-6" data-testid="client-dashboard-home-loading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96 max-w-full" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-xl border bg-card p-4 shadow-sm">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="mt-3 h-6 w-24" />
          </div>
        ))}
      </div>
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-64 w-full" />
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
        delta="KRW"
        icon={<Wallet className="h-4 w-4" />}
        accent="blue"
        testId="client-book-total-aum"
      />
      <KpiCard
        label="고객 수"
        value={`${data.client_count}`}
        delta="활성"
        icon={<Users className="h-4 w-4" />}
        accent="slate"
        testId="client-book-client-count"
      />
      <KpiCard
        label="고위험 고객"
        value={`${highRiskCount}`}
        delta="주의"
        icon={<ShieldAlert className="h-4 w-4" />}
        accent="amber"
        testId="client-book-high-risk"
      />
      <KpiCard
        label="평균 수익률"
        value={formatPct(averageReturnPct, { signed: true })}
        deltaValue={averageReturnPct}
        icon={<TrendingUp className="h-4 w-4" />}
        accent={averageReturnPct >= 0 ? "green" : "rose"}
        testId="client-book-average-return"
      />
    </section>
  );
}

function ClientSelector({
  clients,
  selectedClientId,
  onSelect,
}: {
  clients: ClientRow[];
  selectedClientId: string;
  onSelect: (clientId: string) => void;
}) {
  return (
    <SectionCard
      title="고객 선택"
      testId="client-book"
      action={
        selectedClientId ? (
          <Link
            href={`/clients/${encodeURIComponent(selectedClientId)}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
            data-testid="selected-client-workspace-link"
          >
            워크스페이스 열기
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        ) : null
      }
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {clients.map((client) => {
          const active = client.client_id === selectedClientId;
          return (
            <article
              key={client.client_id}
              className={cn(
                "rounded-md border bg-card shadow-sm transition-colors",
                active ? "border-primary bg-primary/5" : "border-border",
              )}
              data-state={active ? "selected" : undefined}
              data-testid={`client-card-${client.client_id}`}
            >
              <button
                type="button"
                onClick={() => onSelect(client.client_id)}
                className="block min-h-32 w-full p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
                    className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${riskTone(
                      client.risk_grade,
                    )}`}
                  >
                    {riskLabel(client.risk_grade)}
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <p className="text-muted-foreground">관리자산</p>
                    <p className="mt-1 font-semibold tabular-nums">
                      {formatKRWCompact(client.aum_krw)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">보유종목</p>
                    <p className="mt-1 font-semibold tabular-nums">
                      {client.holdings_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">수익률</p>
                    <p
                      className={`mt-1 font-semibold tabular-nums ${signedColorClass(
                        client.total_pnl_pct,
                      )}`}
                    >
                      {formatPct(client.total_pnl_pct, { signed: true })}
                    </p>
                  </div>
                </div>
              </button>

              <div className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground">
                <span>{active ? "선택된 고객" : "클릭하면 대시보드 전환"}</span>
                <Link
                  href={`/clients/${encodeURIComponent(client.client_id)}`}
                  className="inline-flex items-center gap-1 font-semibold text-primary hover:underline"
                  data-testid={`client-workspace-link-${client.client_id}`}
                >
                  워크스페이스 열기
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </SectionCard>
  );
}

function ClientSummaryTable({
  clients,
  selectedClientId,
  onSelect,
}: {
  clients: ClientRow[];
  selectedClientId: string;
  onSelect: (clientId: string) => void;
}) {
  return (
    <section
      aria-label="고객 요약 테이블"
      className="rounded-md border bg-card shadow-sm"
      data-testid="client-book-table"
    >
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">고객 요약</h2>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>고객</TableHead>
            <TableHead className="text-right">관리자산</TableHead>
            <TableHead className="text-right">보유종목</TableHead>
            <TableHead>위험등급</TableHead>
            <TableHead className="text-right">수익률</TableHead>
            <TableHead className="text-right">상세</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {clients.map((client) => {
            const active = client.client_id === selectedClientId;
            return (
              <TableRow
                key={client.client_id}
                className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                data-state={active ? "selected" : undefined}
                data-testid={`client-table-row-${client.client_id}`}
                tabIndex={0}
                onClick={() => onSelect(client.client_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(client.client_id);
                  }
                }}
              >
                <TableCell>
                  <span className="font-medium text-foreground">
                    {client.client_name}
                  </span>
                  <p className="text-xs text-muted-foreground">{client.client_id}</p>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatKRWCompact(client.aum_krw)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {client.holdings_count}
                </TableCell>
                <TableCell>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${riskTone(
                      client.risk_grade,
                    )}`}
                  >
                    {riskLabel(client.risk_grade)}
                  </span>
                </TableCell>
                <TableCell
                  className={`text-right font-semibold tabular-nums ${signedColorClass(
                    client.total_pnl_pct,
                  )}`}
                >
                  {formatPct(client.total_pnl_pct, { signed: true })}
                </TableCell>
                <TableCell className="text-right">
                  <Link
                    href={`/clients/${encodeURIComponent(client.client_id)}`}
                    className="font-medium text-primary hover:underline"
                    data-testid={`client-table-workspace-link-${client.client_id}`}
                    onClick={(event) => event.stopPropagation()}
                  >
                    열기
                  </Link>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </section>
  );
}

export function ClientDashboardHome() {
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const clientsQuery = useQuery({
    queryKey: ["portfolio", "clients"],
    queryFn: getPortfolioClients,
    staleTime: 60_000,
  });

  const data = clientsQuery.data;
  const clients = useMemo(() => data?.clients ?? [], [data?.clients]);

  useEffect(() => {
    if (clients.length === 0) return;
    const selectedExists = clients.some(
      (client) => client.client_id === selectedClientId,
    );
    if (!selectedExists) {
      setSelectedClientId(clients[0]!.client_id);
    }
  }, [clients, selectedClientId]);

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
        description="고객 포트폴리오 데이터를 업로드하거나 생성하면 통합 홈을 시작할 수 있습니다."
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="client-dashboard-home">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            PB 고객관리
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">고객장부</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            고객을 선택하면 아래 대시보드가 즉시 전환되고, 상세 분석은 워크스페이스에서 이어집니다.
          </p>
        </div>
        <div
          className="rounded-md border bg-card px-3 py-2 text-xs text-muted-foreground"
          data-testid="client-book-count"
        >
          관리 고객 {data.client_count}명
        </div>
      </div>

      <ClientBookSummary data={data} />
      <ClientSelector
        clients={clients}
        selectedClientId={activeClientId}
        onSelect={setSelectedClientId}
      />

      {selectedClient ? (
        <SelectedClientDashboard
          clientId={activeClientId}
          clientName={selectedClient.client_name}
        />
      ) : null}

      <ClientSummaryTable
        clients={clients}
        selectedClientId={activeClientId}
        onSelect={setSelectedClientId}
      />
    </div>
  );
}
