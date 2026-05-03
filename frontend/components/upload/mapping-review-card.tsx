"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type {
  ConfirmedCsvMappingMap,
  CsvMappingCandidateGroup,
  UploadBlockingError,
} from "@/lib/portfolio/upload-import";

type CsvMappingCandidate = CsvMappingCandidateGroup["candidates"] extends
  | (infer Candidate)[]
  | undefined
  ? Candidate
  : never;

const REQUIRED_FIELDS = ["symbol", "quantity", "avg_cost", "currency", "market"] as const;
const OPTIONAL_FIELDS = ["client_id", "account", "broker", "name", "date"] as const;
const ALL_FIELDS = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS] as const;

const FIELD_LABELS: Record<(typeof ALL_FIELDS)[number], string> = {
  symbol: "Symbol",
  quantity: "Quantity",
  avg_cost: "Average cost",
  currency: "Currency",
  market: "Market",
  client_id: "Source client ID",
  account: "Account",
  broker: "Broker",
  name: "Name",
  date: "Date",
};

function optionLabel(candidate: CsvMappingCandidate): string {
  const confidence = `${Math.round(candidate.confidence * 100)}%`;
  if (candidate.type === "derived") {
    return `derived: ${candidate.method ?? "symbol_pattern"} (${confidence})`;
  }
  return `column: ${candidate.column ?? "-"} (${confidence})`;
}

function toConfirmedMapping(candidate: CsvMappingCandidate): ConfirmedCsvMappingMap[string] {
  if (candidate.type === "derived") {
    return { type: "derived", method: candidate.method ?? "symbol_pattern" };
  }
  return { type: "column", column: candidate.column ?? "" };
}

function getPreviewColumns(rows: Record<string, unknown>[]): string[] {
  const columns = new Set<string>();
  for (const row of rows.slice(0, 5)) {
    Object.keys(row).forEach((column) => columns.add(column));
  }
  return [...columns];
}

export function MappingReviewCard({
  candidates,
  normalizedPreview,
  blockingErrors = [],
  importing,
  onConfirm,
}: {
  candidates: CsvMappingCandidateGroup[];
  normalizedPreview: Record<string, unknown>[];
  blockingErrors?: UploadBlockingError[];
  importing?: boolean;
  onConfirm: (mapping: ConfirmedCsvMappingMap) => void | Promise<void>;
}) {
  const candidatesByField = useMemo(() => {
    return new Map(candidates.map((group) => [group.standard_field, group.candidates ?? []]));
  }, [candidates]);

  const initialSelection = useMemo(() => {
    const next: Record<string, string> = {};
    for (const field of ALL_FIELDS) {
      const fieldCandidates = candidatesByField.get(field) ?? [];
      next[field] = fieldCandidates.length > 0 ? "0" : "";
    }
    return next;
  }, [candidatesByField]);

  const [selection, setSelection] = useState<Record<string, string>>(initialSelection);

  useEffect(() => {
    setSelection(initialSelection);
  }, [initialSelection]);

  const missingRequiredFields = REQUIRED_FIELDS.filter((field) => {
    const fieldCandidates = candidatesByField.get(field) ?? [];
    return !selection[field] || !fieldCandidates[Number(selection[field])];
  });
  const previewColumns = getPreviewColumns(normalizedPreview);

  const handleConfirm = () => {
    const confirmed: ConfirmedCsvMappingMap = {};
    for (const field of ALL_FIELDS) {
      const selectedIndex = selection[field];
      if (!selectedIndex) continue;
      const candidate = (candidatesByField.get(field) ?? [])[Number(selectedIndex)];
      if (!candidate) continue;
      confirmed[field] = toConfirmedMapping(candidate);
    }
    void onConfirm(confirmed);
  };

  return (
    <Card className="md:col-span-2" data-testid="mapping-review-card">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-sm font-semibold">PB 매핑 확인</CardTitle>
          <div className="inline-flex items-center gap-1 rounded-md border bg-muted/30 px-2 py-1 text-xs text-muted-foreground">
            <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
            고객 저장 전 확인 필요
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {ALL_FIELDS.map((field) => {
            const fieldCandidates = candidatesByField.get(field) ?? [];
            const selectedCandidate = fieldCandidates[Number(selection[field] || -1)];
            const required = REQUIRED_FIELDS.includes(field as (typeof REQUIRED_FIELDS)[number]);

            return (
              <div key={field} className="rounded-md border bg-muted/20 p-3">
                <label
                  className="mb-1 block text-xs font-semibold text-muted-foreground"
                  htmlFor={`mapping-select-${field}`}
                >
                  {FIELD_LABELS[field]}
                  {required && <span className="ml-1 text-destructive">*</span>}
                </label>
                <select
                  id={`mapping-select-${field}`}
                  data-testid={`mapping-select-${field}`}
                  value={selection[field] ?? ""}
                  onChange={(event) =>
                    setSelection((current) => ({ ...current, [field]: event.target.value }))
                  }
                  disabled={importing || fieldCandidates.length === 0}
                  className="h-9 w-full rounded-md border bg-background px-2 text-xs outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">{required ? "필수 매핑 없음" : "매핑 안 함"}</option>
                  {fieldCandidates.map((candidate, index) => (
                    <option key={`${candidate.type}-${candidate.column ?? candidate.method}-${index}`} value={String(index)}>
                      {optionLabel(candidate)}
                    </option>
                  ))}
                </select>
                {selectedCandidate && (
                  <p className="mt-1 text-xs text-muted-foreground">{selectedCandidate.reason}</p>
                )}
              </div>
            );
          })}
        </div>

        {blockingErrors.length > 0 && (
          <div className="space-y-1 rounded-md border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-xs font-semibold text-destructive">막힌 row</p>
            {blockingErrors.slice(0, 5).map((error, index) => (
              <div key={`${error.row}-${error.column ?? "row"}-${index}`} className="text-xs text-destructive">
                R{error.row} {error.column ? `${error.column}: ` : ""}
                {error.message}
              </div>
            ))}
          </div>
        )}

        {normalizedPreview.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40">
                <tr>
                  {previewColumns.map((column) => (
                    <th key={column} className="px-2 py-2 font-mono font-semibold">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {normalizedPreview.slice(0, 5).map((row, rowIndex) => (
                  <tr key={rowIndex} className="border-t">
                    {previewColumns.map((column) => (
                      <td key={column} className="px-2 py-2 font-mono">
                        {String(row[column] ?? "-")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            필수 5개 필드가 모두 확정되어야 고객 워크스페이스에 저장됩니다.
          </p>
          <Button
            type="button"
            size="sm"
            disabled={importing || missingRequiredFields.length > 0}
            onClick={handleConfirm}
            data-testid="confirm-mapping-import"
          >
            <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
            매핑 확정 후 저장
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
