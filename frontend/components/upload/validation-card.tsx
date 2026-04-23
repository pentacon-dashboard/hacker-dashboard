"use client";

import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export interface ValidationResult {
  upload_id: string;
  filename: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  warning_rows: number;
  columns_detected: string[];
  preview_rows: Record<string, string>[];
  errors: { row: number; column: string; message: string }[];
  warnings: { row: number; column: string; message: string }[];
}

interface ValidationCardProps {
  result?: ValidationResult | null;
  loading?: boolean;
  error?: string | null;
}

export function ValidationCard({ result, loading, error }: ValidationCardProps) {
  return (
    <Card data-testid="validation-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">2. 데이터 검증 상태</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <div className="grid grid-cols-2 gap-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive">
            <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            {error}
          </div>
        )}

        {!loading && !error && !result && (
          <div className="flex min-h-[80px] items-center justify-center text-sm text-muted-foreground">
            파일 업로드 후 검증 결과가 표시됩니다
          </div>
        )}

        {result && !loading && (
          <div className="space-y-3">
            {/* 컬럼 감지 */}
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2">
              <p className="text-xs font-medium text-muted-foreground mb-1">감지된 컬럼</p>
              <div className="flex flex-wrap gap-1">
                {result.columns_detected.map((col) => (
                  <span
                    key={col}
                    className="rounded bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>

            {/* 4 카운트 그리드 */}
            <div className="grid grid-cols-2 gap-2" data-testid="validation-counts">
              <div className="rounded-lg border border-border bg-card px-3 py-2 text-center">
                <p className="text-2xl font-bold tabular-nums">{result.total_rows}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">총 행</p>
              </div>
              <div className="rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-green-500">
                  <CheckCircle className="h-4 w-4" aria-hidden="true" />
                  {result.valid_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">검증 완료</p>
              </div>
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-destructive">
                  <XCircle className="h-4 w-4" aria-hidden="true" />
                  {result.error_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">오류</p>
              </div>
              <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-yellow-500">
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                  {result.warning_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">경고</p>
              </div>
            </div>

            {/* 오류 목록 (최대 3개) */}
            {result.errors.length > 0 && (
              <div className="space-y-1">
                {result.errors.slice(0, 3).map((e, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 rounded border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive"
                  >
                    <span className="font-mono">R{e.row}</span>
                    <span className="text-muted-foreground">{e.column}:</span>
                    <span>{e.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
