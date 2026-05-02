"use client";

import Link from "next/link";
import type { HoldingDetail } from "@/lib/api/portfolio";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  formatKRWCompact,
  formatPct,
  signedColorClass,
} from "@/lib/utils/format";
import { useLocale } from "@/lib/i18n/locale-provider";
import { formatSymbolDisplay } from "@/lib/market/display";

interface TopHoldingsTableProps {
  holdings: HoldingDetail[];
  limit?: number;
  totalValueKrw?: number;
  compact?: boolean;
  /** 평균가 컬럼 표시 여부 (7컬럼 모드) */
  showAvgCost?: boolean;
  /** 현재가 컬럼 표시 여부 (7컬럼 모드) */
  showCurrentPrice?: boolean;
}

export function TopHoldingsTable({
  holdings,
  limit = 5,
  totalValueKrw,
  compact = false,
  showAvgCost = false,
  showCurrentPrice = false,
}: TopHoldingsTableProps) {
  const { t } = useLocale();
  if (holdings.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        {t("dashboard.emptyHoldings")}
      </div>
    );
  }

  const sorted = [...holdings]
    .sort((a, b) => Number(b.value_krw) - Number(a.value_krw))
    .slice(0, limit);

  const totalForWeight =
    totalValueKrw ??
    holdings.reduce((acc, h) => acc + Number(h.value_krw), 0);

  return (
    <div className="w-full" data-testid="top-holdings-table">
      <Table className={compact ? "table-fixed" : undefined}>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {compact ? null : (
              <TableHead className="h-7 w-6 px-1 text-[10px]">#</TableHead>
            )}
            <TableHead
              className={
                compact
                  ? "h-7 w-[54%] px-1 text-[10px]"
                  : "h-7 px-1 text-[10px]"
              }
            >
              {t("table.symbol")}
            </TableHead>
            {compact ? null : (
              <TableHead className="h-7 px-1 text-[10px]">
                {t("table.market")}
              </TableHead>
            )}
            {showAvgCost && !compact && (
              <TableHead className="h-7 px-1 text-right text-[10px]">{t("table.avgCost")}</TableHead>
            )}
            {showCurrentPrice && !compact && (
              <TableHead className="h-7 px-1 text-right text-[10px]">{t("table.currentPrice")}</TableHead>
            )}
            <TableHead
              className={
                compact
                  ? "h-7 w-[46%] px-1 text-right text-[10px]"
                  : "h-7 px-1 text-right text-[10px]"
              }
            >
              {compact ? (
                <span className="inline-flex flex-col items-end leading-tight">
                  <span>{t("table.value")}</span>
                  <span>{t("table.return")}</span>
                </span>
              ) : (
                t("table.value")
              )}
            </TableHead>
            {compact ? null : (
              <TableHead className="h-7 px-1 text-right text-[10px]">
                {t("table.return")}
              </TableHead>
            )}
            {compact ? null : (
              <TableHead className="h-7 px-1 text-right text-[10px]">
                {t("table.weight")}
              </TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((h, idx) => {
            const pnlNum = Number(h.pnl_pct);
            const weight =
              totalForWeight > 0
                ? (Number(h.value_krw) / totalForWeight) * 100
                : 0;
            const fullSymbolLabel = formatSymbolDisplay(h.market, h.code);
            const shortSymbolLabel = formatSymbolDisplay(h.market, h.code, {
              includeCode: false,
            });
            return (
              <TableRow key={h.id}>
                {compact ? null : (
                  <TableCell className="px-1 py-1.5 text-[11px] text-muted-foreground">
                    {idx + 1}
                  </TableCell>
                )}
                <TableCell className="px-1 py-1.5">
                  <div className={compact ? "flex min-w-0 items-center gap-2" : undefined}>
                    {compact ? (
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {idx + 1}
                      </span>
                    ) : null}
                    <Link
                      href={`/symbol/${h.market}/${encodeURIComponent(h.code)}`}
                      className={
                        compact
                          ? "min-w-0 break-keep text-xs font-medium leading-tight hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          : "block truncate text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      }
                      title={fullSymbolLabel}
                      aria-label={fullSymbolLabel}
                    >
                      {shortSymbolLabel}
                    </Link>
                  </div>
                </TableCell>
                {compact ? null : (
                  <TableCell className="px-1 py-1.5 text-[11px] uppercase text-muted-foreground">
                    {h.market}
                  </TableCell>
                )}
                {showAvgCost && !compact && (
                  <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums text-muted-foreground">
                    {formatKRWCompact(h.avg_cost)}
                  </TableCell>
                )}
                {showCurrentPrice && !compact && (
                  <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums">
                    {formatKRWCompact(h.current_price_krw)}
                  </TableCell>
                )}
                <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums">
                  {compact ? (
                    <div className="flex flex-col items-end gap-0.5">
                      <span>{formatKRWCompact(h.value_krw)}</span>
                      <span
                        className={`font-semibold ${signedColorClass(pnlNum)}`}
                      >
                        {formatPct(h.pnl_pct, { signed: true })}
                      </span>
                    </div>
                  ) : (
                    formatKRWCompact(h.value_krw)
                  )}
                </TableCell>
                {compact ? null : (
                  <TableCell
                    className={`px-1 py-1.5 text-right text-[11px] font-semibold tabular-nums ${signedColorClass(pnlNum)}`}
                  >
                    {formatPct(h.pnl_pct, { signed: true })}
                  </TableCell>
                )}
                {compact ? null : (
                  <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums text-muted-foreground">
                    {weight.toFixed(1)}%
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
