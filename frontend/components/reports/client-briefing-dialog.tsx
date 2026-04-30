"use client";

import { useState } from "react";
import { Download, FileText, Printer } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  createClientBriefingReport,
  type ClientBriefingReportResponse,
} from "@/lib/api/portfolio";

interface ClientBriefingDialogProps {
  clientId: string;
  clientName?: string | null;
}

function statusTone(status: ClientBriefingReportResponse["status"]): string {
  if (status === "success") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "warning") return "border-amber-200 bg-amber-50 text-amber-700";
  if (status === "degraded") return "border-orange-200 bg-orange-50 text-orange-700";
  return "border-red-200 bg-red-50 text-red-700";
}

function gateTone(value: string): string {
  if (value.startsWith("pass")) return "border-emerald-200 text-emerald-700";
  if (value.startsWith("skip")) return "border-slate-200 text-slate-600";
  return "border-red-200 text-red-700";
}

function downloadReport(clientId: string, script: string) {
  const blob = new Blob([script], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${clientId}-briefing.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ClientBriefingDialog({
  clientId,
  clientName,
}: ClientBriefingDialogProps) {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<ClientBriefingReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadReport() {
    setIsLoading(true);
    setError(null);
    try {
      const next = await createClientBriefingReport({ client_id: clientId });
      setReport(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "브리핑 리포트 생성에 실패했습니다.");
      setReport(null);
    } finally {
      setIsLoading(false);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen && !report && !isLoading) {
      void loadReport();
    }
  }

  const exportReady = Boolean(report?.export_ready && report.report_script);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-2">
          <FileText className="h-4 w-4" />
          브리핑 리포트
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[88vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>고객 브리핑 리포트</DialogTitle>
          <DialogDescription>
            {clientName ?? clientId} 포트폴리오의 계산값과 근거를 기준으로 생성합니다.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {isLoading && (
            <div className="rounded-md border p-4 text-sm text-muted-foreground">
              리포트 생성 중입니다.
            </div>
          )}

          {error && (
            <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {report && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className={statusTone(report.status)}>
                  {report.status}
                </Badge>
                {Object.entries(report.gate_results).map(([gate, value]) => (
                  <Badge key={gate} variant="outline" className={gateTone(value)}>
                    {gate}: {value}
                  </Badge>
                ))}
              </div>

              {report.sections.length === 0 ? (
                <div className="rounded-md border p-4 text-sm text-muted-foreground">
                  근거가 부족해 고객용 리포트를 만들 수 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {report.sections.map((section) => (
                    <section key={section.title} className="rounded-md border p-4">
                      <h3 className="text-sm font-semibold">{section.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {section.body}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(section.evidence ?? []).map((item) => (
                          <Badge
                            key={`${section.title}-${item.type}-${item.ref}`}
                            variant="outline"
                          >
                            {item.type}:{item.ref}
                          </Badge>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              )}

              {report.report_script && (
                <pre className="max-h-56 overflow-auto rounded-md border bg-muted p-3 text-xs leading-5">
                  {report.report_script}
                </pre>
              )}
            </>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button type="button" variant="outline" onClick={() => void loadReport()}>
            새로 생성
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!exportReady}
            onClick={() => window.print()}
            className="gap-2"
          >
            <Printer className="h-4 w-4" />
            인쇄
          </Button>
          <Button
            type="button"
            disabled={!exportReady}
            onClick={() => {
              if (report?.report_script) downloadReport(clientId, report.report_script);
            }}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            다운로드
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
