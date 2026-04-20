"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { deleteHolding, type HoldingDetail } from "@/lib/api/portfolio";
import {
  formatKRW,
  formatPct,
  formatSignedNumber,
  signedColorClass,
} from "@/lib/utils/format";

type SortKey = "pnl_pct" | "value_krw";

const CURRENCY_OPTIONS = ["전체", "KRW", "USD", "USDT"] as const;
type CurrencyFilter = (typeof CURRENCY_OPTIONS)[number];

interface HoldingsTableProps {
  holdings: HoldingDetail[];
}

export function HoldingsTable({ holdings }: HoldingsTableProps) {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("value_krw");
  const [currencyFilter, setCurrencyFilter] =
    useState<CurrencyFilter>("전체");

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteHolding(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["portfolio", "summary"] });
      await queryClient.invalidateQueries({
        queryKey: ["portfolio", "holdings"],
      });
    },
  });

  const filtered =
    currencyFilter === "전체"
      ? holdings
      : holdings.filter((h) => h.currency === currencyFilter);

  const sorted = [...filtered].sort((a, b) => {
    const aVal = Number(a[sortKey]);
    const bVal = Number(b[sortKey]);
    return bVal - aVal;
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">통화 필터:</span>
        {CURRENCY_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => setCurrencyFilter(opt)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              currencyFilter === opt
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {opt}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">정렬:</span>
        <button
          onClick={() => setSortKey("value_krw")}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            sortKey === "value_krw"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          평가금액
        </button>
        <button
          onClick={() => setSortKey("pnl_pct")}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            sortKey === "pnl_pct"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          손익률
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <Table data-testid="holdings-table">
          <TableHeader>
            <TableRow>
              <TableHead>심볼</TableHead>
              <TableHead>수량</TableHead>
              <TableHead className="text-right">평단가</TableHead>
              <TableHead className="text-right">현재가</TableHead>
              <TableHead className="text-right">평가금액(KRW)</TableHead>
              <TableHead className="text-right">손익(KRW)</TableHead>
              <TableHead className="text-right">손익률</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((holding) => {
              const pnlColor = signedColorClass(holding.pnl_krw);
              return (
                <TableRow key={holding.id}>
                  <TableCell>
                    <div className="flex flex-col gap-0.5">
                      <Link
                        href={`/symbol/${encodeURIComponent(holding.market)}/${encodeURIComponent(holding.code)}`}
                        className="font-medium hover:underline focus:outline-none focus:ring-2 focus:ring-ring rounded"
                      >
                        {holding.code}
                      </Link>
                      <Badge variant="secondary" className="w-fit text-[10px]">
                        {holding.market}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {Number(holding.quantity).toLocaleString("ko-KR", {
                      maximumFractionDigits: 8,
                    })}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm">
                    {Number(holding.avg_cost).toLocaleString("ko-KR")}
                    <span className="ml-1 text-xs text-muted-foreground">
                      {holding.currency}
                    </span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm">
                    {Number(holding.current_price).toLocaleString("ko-KR")}
                    <span className="ml-1 text-xs text-muted-foreground">
                      {holding.currency}
                    </span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatKRW(holding.value_krw)}
                  </TableCell>
                  <TableCell className={`text-right tabular-nums ${pnlColor}`}>
                    {formatSignedNumber(holding.pnl_krw)}
                  </TableCell>
                  <TableCell className={`text-right tabular-nums ${pnlColor}`}>
                    {formatPct(holding.pnl_pct, { signed: true })}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      aria-label={`${holding.code} 삭제`}
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(holding.id)}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        aria-hidden="true"
                      >
                        <path d="M3 6h18" />
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                      </svg>
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
