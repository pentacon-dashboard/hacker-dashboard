"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocale } from "@/lib/i18n/locale-provider";

interface PreviewTableProps {
  columns?: string[];
  rows?: Record<string, string>[];
  loading?: boolean;
}

export function PreviewTable({ columns, rows, loading }: PreviewTableProps) {
  const { t } = useLocale();
  return (
    <Card data-testid="preview-table">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{t("upload.section.preview")}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {loading && (
          <div className="px-6 py-3 space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        )}

        {!loading && (!columns || columns.length === 0) && (
          <div className="flex min-h-[80px] items-center justify-center text-sm text-muted-foreground px-6 py-4">
            {t("upload.preview.pending")}
          </div>
        )}

        {columns && columns.length > 0 && rows && !loading && (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((col) => (
                    <TableHead key={col} className="text-xs font-mono">
                      {col}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.slice(0, 5).map((row, i) => (
                  <TableRow key={i}>
                    {columns.map((col) => (
                      <TableCell key={col} className="text-xs font-mono">
                        {row[col] ?? "-"}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
