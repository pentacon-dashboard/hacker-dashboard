"use client";

import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocale } from "@/lib/i18n/locale-provider";
import type { components } from "@shared/types/api";

type UploadImportStatus = components["schemas"]["UploadImportResponse"]["status"];
type CsvMappingCandidateGroup =
  components["schemas"]["CsvMappingCandidateGroup"];
type NormalizedCsvHolding = components["schemas"]["NormalizedCsvHolding"];
type UploadImportRow = components["schemas"]["UploadImportRow"];

export interface ValidationResult {
  upload_id: string;
  filename?: string;
  file_content_hash?: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  warning_rows: number;
  columns_detected?: string[];
  preview_rows?: Record<string, string>[];
  preview?: Record<string, string>[];
  errors?: { row: number; column?: string | null; code?: string; message: string }[];
  warnings?: { row: number; column?: string | null; code?: string; message: string }[];
  schema_fingerprint?: string;
  created_at?: string;
  import_status?: UploadImportStatus;
  mapping_candidates?: CsvMappingCandidateGroup[];
  normalized_preview?: Record<string, unknown>[];
  normalized_holdings?: NormalizedCsvHolding[];
  normalization_warnings?: string[];
  imported_rows?: UploadImportRow[];
  recoverable_rows?: UploadImportRow[];
  quarantined_rows?: UploadImportRow[];
  garbage_rows?: UploadImportRow[];
}

interface ValidationCardProps {
  result?: ValidationResult | null;
  loading?: boolean;
  error?: string | null;
}

export function ValidationCard({ result, loading, error }: ValidationCardProps) {
  const { t } = useLocale();
  const previewRows = result?.preview_rows ?? result?.preview ?? [];
  const columnsDetected = result?.columns_detected ?? Object.keys(previewRows[0] ?? {});
  const errors = result?.errors ?? [];
  const hasRowLedger = [
    result?.imported_rows,
    result?.recoverable_rows,
    result?.quarantined_rows,
    result?.garbage_rows,
  ].some(Array.isArray);
  const rowClassificationCounts = {
    imported: result?.imported_rows?.length ?? 0,
    review: result?.recoverable_rows?.length ?? 0,
    quarantine: result?.quarantined_rows?.length ?? 0,
    garbage: result?.garbage_rows?.length ?? 0,
  };

  return (
    <Card data-testid="validation-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{t("upload.section.validation")}</CardTitle>
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
            {t("upload.validation.pending")}
          </div>
        )}

        {result && !loading && (
          <div className="space-y-3">
            {/* 컬럼 감지 */}
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2">
              <p className="text-xs font-medium text-muted-foreground mb-1">{t("upload.validation.columns")}</p>
              <div className="flex flex-wrap gap-1">
                {columnsDetected.map((col) => (
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
                <p className="mt-0.5 text-xs text-muted-foreground">{t("upload.validation.totalRows")}</p>
              </div>
              <div className="rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-green-500">
                  <CheckCircle className="h-4 w-4" aria-hidden="true" />
                  {result.valid_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{t("upload.validation.validRows")}</p>
              </div>
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-destructive">
                  <XCircle className="h-4 w-4" aria-hidden="true" />
                  {result.error_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{t("upload.validation.errorRows")}</p>
              </div>
              <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-center">
                <p className="flex items-center justify-center gap-1 text-2xl font-bold tabular-nums text-yellow-500">
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                  {result.warning_rows}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{t("upload.validation.warningRows")}</p>
              </div>
            </div>

            {hasRowLedger && (
              <div
                className="grid grid-cols-4 gap-2 rounded-lg border border-border bg-muted/20 p-2"
                data-testid="validation-row-classification-counts"
              >
                <div className="text-center">
                  <p
                    className="text-sm font-semibold tabular-nums text-green-600 dark:text-green-400"
                    data-testid="validation-imported-count"
                  >
                    {rowClassificationCounts.imported}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Imported</p>
                </div>
                <div className="text-center">
                  <p
                    className="text-sm font-semibold tabular-nums text-yellow-600 dark:text-yellow-300"
                    data-testid="validation-review-count"
                  >
                    {rowClassificationCounts.review}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Review</p>
                </div>
                <div className="text-center">
                  <p
                    className="text-sm font-semibold tabular-nums text-orange-600 dark:text-orange-300"
                    data-testid="validation-quarantine-count"
                  >
                    {rowClassificationCounts.quarantine}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Quarantine</p>
                </div>
                <div className="text-center">
                  <p
                    className="text-sm font-semibold tabular-nums text-muted-foreground"
                    data-testid="validation-garbage-count"
                  >
                    {rowClassificationCounts.garbage}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Garbage</p>
                </div>
              </div>
            )}

            {/* 오류 목록 (최대 3개) */}
            {errors.length > 0 && (
              <div className="space-y-1">
                {errors.slice(0, 3).map((e, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 rounded border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive"
                  >
                    <span className="font-mono">R{e.row}</span>
                    {e.column && <span className="text-muted-foreground">{e.column}:</span>}
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
