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

interface TopHoldingsTableProps {
  holdings: HoldingDetail[];
  limit?: number;
  totalValueKrw?: number;
}

export function TopHoldingsTable({
  holdings,
  limit = 5,
  totalValueKrw,
}: TopHoldingsTableProps) {
  if (holdings.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        보유 자산 없음
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
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="h-7 w-6 px-1 text-[10px]">#</TableHead>
            <TableHead className="h-7 px-1 text-[10px]">종목</TableHead>
            <TableHead className="h-7 px-1 text-[10px]">시장</TableHead>
            <TableHead className="h-7 px-1 text-right text-[10px]">평가액</TableHead>
            <TableHead className="h-7 px-1 text-right text-[10px]">수익률</TableHead>
            <TableHead className="h-7 px-1 text-right text-[10px]">비중</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((h, idx) => {
            const pnlNum = Number(h.pnl_pct);
            const weight =
              totalForWeight > 0
                ? (Number(h.value_krw) / totalForWeight) * 100
                : 0;
            return (
              <TableRow key={h.id}>
                <TableCell className="px-1 py-1.5 text-[11px] text-muted-foreground">
                  {idx + 1}
                </TableCell>
                <TableCell className="px-1 py-1.5">
                  <Link
                    href={`/symbol/${h.market}/${encodeURIComponent(h.code)}`}
                    className="truncate text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {h.code}
                  </Link>
                </TableCell>
                <TableCell className="px-1 py-1.5 text-[11px] uppercase text-muted-foreground">
                  {h.market}
                </TableCell>
                <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums">
                  {formatKRWCompact(h.value_krw)}
                </TableCell>
                <TableCell
                  className={`px-1 py-1.5 text-right text-[11px] font-semibold tabular-nums ${signedColorClass(pnlNum)}`}
                >
                  {formatPct(h.pnl_pct, { signed: true })}
                </TableCell>
                <TableCell className="px-1 py-1.5 text-right text-[11px] tabular-nums text-muted-foreground">
                  {weight.toFixed(1)}%
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
