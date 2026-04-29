"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { RebalanceAction } from "@/lib/api/rebalance";
import { formatKRW } from "@/lib/utils/format";

const ASSET_CLASS_LABELS: Record<string, string> = {
  stock_kr: "한국 주식",
  stock_us: "미국 주식",
  crypto: "암호화폐",
  cash: "현금",
  fx: "외환",
};

function sortActions(actions: RebalanceAction[]): RebalanceAction[] {
  return [...actions].sort((a, b) => {
    // sell 먼저
    if (a.action !== b.action) return a.action === "sell" ? -1 : 1;
    // asset_class 알파벳
    if (a.asset_class !== b.asset_class)
      return a.asset_class.localeCompare(b.asset_class);
    // code 알파벳
    return a.code.localeCompare(b.code);
  });
}

interface RebalanceActionTableProps {
  actions: RebalanceAction[];
}

export function RebalanceActionTable({ actions }: RebalanceActionTableProps) {
  if (actions.length === 0) {
    return (
      <Card data-testid="rebalance-action-table">
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center space-y-2">
            <p className="text-lg font-medium">리밸런싱 필요 없음</p>
            <p className="text-sm text-muted-foreground">
              현재 포트폴리오가 목표 비중에 근접합니다.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const sorted = sortActions(actions);

  return (
    <Table data-testid="rebalance-action-table">
      <TableHeader>
        <TableRow>
          <TableHead>종류</TableHead>
          <TableHead>종목</TableHead>
          <TableHead>자산군</TableHead>
          <TableHead className="text-right">수량</TableHead>
          <TableHead className="text-right">예상 금액 (KRW)</TableHead>
          <TableHead>이유</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((action, idx) => (
          <TableRow key={`${action.action}-${action.market}-${action.code}-${idx}`}>
            <TableCell>
              {action.action === "buy" ? (
                <Badge
                  data-testid="action-badge-buy"
                  className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-300 dark:border-green-700"
                  variant="outline"
                >
                  매수
                </Badge>
              ) : (
                <Badge
                  data-testid="action-badge-sell"
                  className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-300 dark:border-red-700"
                  variant="outline"
                >
                  매도
                </Badge>
              )}
            </TableCell>
            <TableCell className="font-mono text-xs">
              {action.market} / {action.code}
            </TableCell>
            <TableCell>
              {ASSET_CLASS_LABELS[action.asset_class] ?? action.asset_class}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {Number(action.quantity).toFixed(2)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {action.estimated_value_krw != null ? (
                formatKRW(action.estimated_value_krw)
              ) : (
                <Badge
                  data-testid="value-failed-badge"
                  variant="outline"
                  className="text-muted-foreground"
                >
                  조회 실패
                </Badge>
              )}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground max-w-xs whitespace-pre-wrap break-words">
              {action.reason}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
