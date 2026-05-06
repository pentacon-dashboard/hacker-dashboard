"use client";

import { AlertTriangle, ArrowRight, Info } from "lucide-react";
import Link from "next/link";
import type { PortfolioSummary, SnapshotResponse } from "@/lib/api/portfolio";
import { cn } from "@/lib/utils";
import { formatKRWCompact, formatPct, signedColorClass } from "@/lib/utils/format";
import {
  buildAssetClassEvidenceRows,
  buildHoldingDistributionRows,
  buildPeriodSnapshotStats,
  buildTopHoldingWeightRows,
  hasComparableHoldingSnapshots,
  hhiFormulaLabel,
  type AssetClassEvidenceRow,
  type HoldingDistributionRow,
  type HoldingWeightRow,
} from "./kpi-evidence-utils";

export type KpiEvidenceKey =
  | "totalAssets"
  | "dailyChange"
  | "periodChange"
  | "holdings"
  | "concentration";

interface KpiEvidencePanelProps {
  activeKey: KpiEvidenceKey;
  clientId: string;
  summary: PortfolioSummary;
  snapshots: SnapshotResponse[];
  hiddenHoldingCount: number;
  panelId: string;
}

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "국내주식",
  stock_us: "미국주식",
  crypto: "가상자산",
  cash: "현금",
  fx: "외화",
  other: "기타",
};

function toNumber(value: number | string | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function clientHref(clientId: string): string {
  return `/clients/${encodeURIComponent(clientId)}`;
}

function clientNewsHref(clientId: string): string {
  return `/news?client_id=${encodeURIComponent(clientId)}`;
}

function displayAssetClassLabel(key: string, fallback: string): string {
  return ASSET_CLASS_LABELS[key] ?? fallback;
}

function EvidenceAction({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md border bg-card px-3 text-sm font-semibold text-primary transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="truncate">{label}</span>
      <ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
    </Link>
  );
}

function EvidenceShell({
  panelId,
  title,
  value,
  summary,
  action,
  children,
}: {
  panelId: string;
  title: string;
  value: string;
  summary: string;
  action: React.ReactNode;
  children: React.ReactNode;
}) {
  const titleId = `${panelId}-title`;

  return (
    <section
      id={panelId}
      role="region"
      aria-labelledby={titleId}
      className="rounded-xl border bg-card p-4 shadow-sm"
    >
      <header className="flex min-w-0 flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <h2
            id={titleId}
            className="break-keep text-sm font-semibold tracking-tight text-foreground"
          >
            {title}
          </h2>
          <p className="mt-2 min-w-0 max-w-full truncate text-2xl font-bold tabular-nums text-foreground">
            {value}
          </p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{summary}</p>
        </div>
        {action}
      </header>
      <div className="mt-4 grid min-w-0 gap-3 lg:grid-cols-2">{children}</div>
    </section>
  );
}

function EvidenceBlock({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 rounded-lg border bg-background/60 p-3", className)}>
      <h3 className="mb-3 break-keep text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {children}
    </div>
  );
}

function DegradedBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-sm font-semibold">{title}</p>
        <div className="mt-1 text-sm leading-6">{children}</div>
      </div>
    </div>
  );
}

function SourceDetails({ items }: { items: string[] }) {
  return (
    <details className="min-w-0 text-sm text-muted-foreground">
      <summary className="flex cursor-pointer items-center gap-2 rounded-md text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>출처 상세</span>
      </summary>
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item} className="flex min-w-0 gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="min-w-0 break-words [overflow-wrap:anywhere] leading-6">
              {item}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function MetricTerm({
  label,
  value,
  description,
  valueClassName,
}: {
  label: string;
  value: string;
  description?: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex min-w-0 items-start justify-between gap-3 border-b py-2 last:border-b-0">
      <div className="min-w-0">
        <dt className="truncate text-sm font-medium text-foreground">{label}</dt>
        {description ? (
          <dd className="mt-0.5 break-keep text-xs leading-5 text-muted-foreground">
            {description}
          </dd>
        ) : null}
      </div>
      <dd
        className={cn(
          "shrink-0 whitespace-nowrap text-sm font-semibold tabular-nums",
          valueClassName,
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function AssetClassRows({ rows }: { rows: AssetClassEvidenceRow[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">표시할 자산군 근거가 없습니다.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <dl className="min-w-[260px]">
        {rows.map((row) => (
          <MetricTerm
            key={row.key}
            label={displayAssetClassLabel(row.key, row.label)}
            value={formatPct(row.ratio * 100)}
            description={formatKRWCompact(row.valueKrw)}
          />
        ))}
      </dl>
    </div>
  );
}

function HoldingDistributionList({ rows }: { rows: HoldingDistributionRow[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">분류된 보유종목이 없습니다.</p>;
  }

  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li
          key={row.key}
          className="flex min-w-0 items-center justify-between gap-3 rounded-md bg-muted/40 px-3 py-2"
        >
          <span className="min-w-0 truncate text-sm font-medium">
            {displayAssetClassLabel(row.key, row.label)}
          </span>
          <span className="shrink-0 text-sm font-semibold tabular-nums">
            {row.count}개
          </span>
        </li>
      ))}
    </ul>
  );
}

function HoldingWeightList({ rows }: { rows: HoldingWeightRow[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">상위 보유종목 근거가 없습니다.</p>;
  }

  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li
          key={row.id}
          className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-3 rounded-md bg-muted/40 px-3 py-2"
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{row.code}</p>
            <p className="truncate text-xs text-muted-foreground">{row.market}</p>
          </div>
          <div className="text-right">
            <p className="whitespace-nowrap text-sm font-semibold tabular-nums">
              {formatPct(row.weightPct)}
            </p>
            <p
              className={cn(
                "whitespace-nowrap text-xs font-medium tabular-nums",
                signedColorClass(row.pnlPct),
              )}
            >
              {formatPct(row.pnlPct, { signed: true })}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function KpiEvidencePanel({
  activeKey,
  clientId,
  summary,
  snapshots,
  hiddenHoldingCount,
  panelId,
}: KpiEvidencePanelProps) {
  const totalValueKrw = toNumber(summary.total_value_krw);
  const assetClassRows = buildAssetClassEvidenceRows(summary);
  const topHoldingRows = buildTopHoldingWeightRows(summary.holdings, totalValueKrw, 5);
  const distributionRows = buildHoldingDistributionRows(summary.holdings);
  const periodStats = buildPeriodSnapshotStats(snapshots);
  const comparableHoldings = hasComparableHoldingSnapshots(snapshots);
  const hasUsableAssetClassEvidence =
    totalValueKrw > 0 &&
    assetClassRows.some((row) => row.ratio > 0 && row.valueKrw > 0);

  if (activeKey === "totalAssets") {
    return (
      <EvidenceShell
        panelId={panelId}
        title="총자산 근거"
        value={formatKRWCompact(summary.total_value_krw)}
        summary="총자산은 정규화된 보유종목 평가금액 합계와 자산군 비중을 기준으로 표시합니다."
        action={<EvidenceAction href={clientHref(clientId)} label="고객 상세 보기" />}
      >
        <EvidenceBlock title="자산군 비중">
          <AssetClassRows rows={assetClassRows} />
        </EvidenceBlock>
        <EvidenceBlock title="상위 보유 비중">
          <HoldingWeightList rows={topHoldingRows} />
        </EvidenceBlock>
        <EvidenceBlock title="출처" className="lg:col-span-2">
          <SourceDetails
            items={[
              "portfolio.summary.total_value_krw",
              "portfolio.summary.asset_class_breakdown",
              "portfolio.summary.holdings[].value_krw",
            ]}
          />
        </EvidenceBlock>
      </EvidenceShell>
    );
  }

  if (activeKey === "dailyChange") {
    const dailyPct = toNumber(summary.daily_change_pct);

    return (
      <EvidenceShell
        panelId={panelId}
        title="일간 변동 근거"
        value={formatPct(dailyPct, { signed: true })}
        summary={`${formatKRWCompact(summary.daily_change_krw)} 변동은 요약 API의 확정 지표만 사용합니다.`}
        action={<EvidenceAction href={clientNewsHref(clientId)} label="관련 뉴스 보기" />}
      >
        <EvidenceBlock title="확정 지표">
          <dl>
            <MetricTerm
              label="일간 변화율"
              value={formatPct(dailyPct, { signed: true })}
              valueClassName={signedColorClass(dailyPct)}
            />
            <MetricTerm
              label="일간 변화액"
              value={formatKRWCompact(summary.daily_change_krw)}
              valueClassName={signedColorClass(summary.daily_change_krw)}
            />
          </dl>
        </EvidenceBlock>
        <EvidenceBlock title="종목 기여 근거">
          {comparableHoldings ? (
            <SourceDetails
              items={[
                "첫 스냅샷과 마지막 스냅샷의 종목 식별자가 일치합니다.",
                "이 패널은 확정된 요약 지표만 표시하고 종목별 기여를 추론하지 않습니다.",
              ]}
            />
          ) : (
            <DegradedBlock title="스냅샷 비교 불가">
              종목별 일간 기여를 산출할 수 없습니다. 첫 스냅샷과 마지막 스냅샷의
              holdings_detail 식별자 또는 평가금액 근거가 정렬되지 않았습니다.
            </DegradedBlock>
          )}
        </EvidenceBlock>
      </EvidenceShell>
    );
  }

  if (activeKey === "periodChange") {
    const periodPct = toNumber(summary.period_change_pct);

    return (
      <EvidenceShell
        panelId={panelId}
        title={`${summary.period_days}일 변화 근거`}
        value={formatPct(periodPct, { signed: true })}
        summary="기간 변화는 스냅샷 총 평가금액의 시작값과 종료값을 비교해 검증합니다."
        action={<EvidenceAction href="#client-book-asset-trend" label="추이 자세히 보기" />}
      >
        <EvidenceBlock title="기간 통계">
          {periodStats ? (
            <dl>
              <MetricTerm
                label="시작값"
                value={formatKRWCompact(periodStats.startValueKrw)}
                description={periodStats.startDate}
              />
              <MetricTerm
                label="종료값"
                value={formatKRWCompact(periodStats.endValueKrw)}
                description={periodStats.endDate}
              />
              <MetricTerm label="고점" value={formatKRWCompact(periodStats.highValueKrw)} />
              <MetricTerm label="저점" value={formatKRWCompact(periodStats.lowValueKrw)} />
            </dl>
          ) : (
            <DegradedBlock title="기간 비교 근거 부족">
              스냅샷이 2개 미만이라 기간 시작값과 종료값을 비교할 수 없습니다.
            </DegradedBlock>
          )}
        </EvidenceBlock>
        <EvidenceBlock title="검증 지표">
          <dl>
            <MetricTerm
              label="요약 API 기간 변화율"
              value={formatPct(periodPct, { signed: true })}
              valueClassName={signedColorClass(periodPct)}
            />
            {periodStats ? (
              <MetricTerm
                label="스냅샷 산출 변화율"
                value={formatPct(periodStats.returnPct, { signed: true })}
                valueClassName={signedColorClass(periodStats.returnPct)}
              />
            ) : null}
          </dl>
          <div className="mt-3">
            <DegradedBlock title="기간 종목 기여 근거 부족">
              종목별 기간 기여를 산출할 수 없습니다. 기간 비교는 총 평가금액
              스냅샷과 요약 API 지표만으로 검증하며, 종목별 기간 기여는 추론하지
              않습니다.
            </DegradedBlock>
          </div>
        </EvidenceBlock>
      </EvidenceShell>
    );
  }

  if (activeKey === "holdings") {
    return (
      <EvidenceShell
        panelId={panelId}
        title="보유종목 근거"
        value={`${summary.holdings_count}개`}
        summary="보유종목 수와 분포는 정규화된 holdings 배열에서 집계합니다."
        action={
          <EvidenceAction href={`${clientHref(clientId)}#holdings`} label="보유 테이블 보기" />
        }
      >
        <EvidenceBlock title="자산군별 종목 수">
          <HoldingDistributionList rows={distributionRows} />
        </EvidenceBlock>
        <EvidenceBlock title="상위 보유 비중">
          <HoldingWeightList rows={topHoldingRows} />
        </EvidenceBlock>
        {hiddenHoldingCount > 0 ? (
          <EvidenceBlock title="누락 표시" className="lg:col-span-2">
            <DegradedBlock title="숨김 처리된 보유종목">
              {hiddenHoldingCount}개 보유종목은 가격 또는 통화 근거가 부족해 목록에서
              숨김 처리되었습니다. 집계 근거는 숨기지 않고 경고로 표시합니다.
            </DegradedBlock>
          </EvidenceBlock>
        ) : null}
      </EvidenceShell>
    );
  }

  if (!hasUsableAssetClassEvidence) {
    return (
      <EvidenceShell
        panelId={panelId}
        title="집중도 근거"
        value={formatPct(summary.risk_score_pct)}
        summary="사용 가능한 원천 데이터가 확인될 때까지 자산군 HHI 근거를 표시하지 않습니다."
        action={
          <EvidenceAction href={`${clientHref(clientId)}#rebalance`} label="리밸런싱 검토" />
        }
      >
        <EvidenceBlock title="HHI 근거 없음" className="lg:col-span-2">
          <DegradedBlock title="집중도 근거 저하">
            총자산이 양수가 아니거나 사용 가능한 자산군 비중 근거가 없어 HHI를 뒷받침할 수
            없습니다. 필요한 입력이 확인될 때까지 자산군 HHI 출처 주장을 표시하지 않습니다.
          </DegradedBlock>
        </EvidenceBlock>
      </EvidenceShell>
    );
  }

  return (
    <EvidenceShell
      panelId={panelId}
      title="집중도 근거"
      value={formatPct(summary.risk_score_pct)}
      summary="집중도는 자산군 배분의 쏠림을 설명하는 deterministic 위험 지표입니다."
      action={
        <EvidenceAction href={`${clientHref(clientId)}#rebalance`} label="리밸런싱 검토" />
      }
    >
      <EvidenceBlock title="HHI 산식">
        <p className="break-keep text-sm leading-6 text-muted-foreground">
          {hhiFormulaLabel}
        </p>
        <dl className="mt-3">
          <MetricTerm label="집중도 점수" value={formatPct(summary.risk_score_pct)} />
        </dl>
      </EvidenceBlock>
      <EvidenceBlock title="상위 보유 맥락">
        <HoldingWeightList rows={topHoldingRows} />
      </EvidenceBlock>
      <EvidenceBlock title="출처와 한계" className="lg:col-span-2">
        <SourceDetails
          items={[
            "portfolio.summary.asset_class_breakdown에서 계산한 자산군 HHI입니다.",
            "손실 확률이나 특정 행동 지시가 아니며, 결정은 별도 목표배분과 리밸런싱 규칙으로 검토합니다.",
          ]}
        />
      </EvidenceBlock>
    </EvidenceShell>
  );
}
