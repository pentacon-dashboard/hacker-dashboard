"use client";

import { useCallback, useState } from "react";
import { CheckCircle, Circle, Loader2, AlertCircle, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { analyzeCsv } from "@/lib/api/analyze";
import { API_BASE } from "@/lib/api/client";
import type { AnalyzerConfig } from "./analyzer-config-card";
import { useLocale } from "@/lib/i18n/locale-provider";

type GateStatus = "idle" | "running" | "pass" | "fail";
type GateKey = "router" | "schema" | "domain" | "critique";

interface GateState {
  router: GateStatus;
  schema: GateStatus;
  domain: GateStatus;
  critique: GateStatus;
  done: boolean;
}

const INITIAL_GATES: GateState = {
  router: "idle",
  schema: "idle",
  domain: "idle",
  critique: "idle",
  done: false,
};

// GATE_LABELS는 컴포넌트 내부에서 t() 기반으로 생성

interface GateDetail {
  gate: GateKey;
  status: "pass" | "fail";
  detail?: string;
  reason?: string;
}

interface AnalyzeProgressCardProps {
  uploadId?: string | null;
  file?: File | null;
  config: AnalyzerConfig;
  disabled?: boolean;
  onComplete?: () => void;
}

function statusFromGateValue(value: string | undefined): GateStatus {
  if (!value) return "idle";
  const normalized = value.toLowerCase();
  if (normalized === "fail: all claims supported" || normalized === "all claims supported") {
    return "pass";
  }
  if (normalized.startsWith("pass") || normalized.startsWith("ok")) return "pass";
  if (normalized.startsWith("fail") || normalized.startsWith("error")) return "fail";
  return "idle";
}

function detailFromGateValue(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return value.replace(/^(pass|fail|ok|error)[:\s-]*/i, "").trim() || value;
}

export function AnalyzeProgressCard({
  uploadId,
  file,
  config,
  disabled,
  onComplete,
}: AnalyzeProgressCardProps) {
  const { t } = useLocale();

  const GATE_LABELS: Record<keyof Omit<GateState, "done">, string> = {
    router: t("upload.gate.router"),
    schema: t("upload.gate.schema"),
    domain: t("upload.gate.domain"),
    critique: t("upload.gate.critique"),
  };

  const [gates, setGates] = useState<GateState>(INITIAL_GATES);
  const [gateDetails, setGateDetails] = useState<Record<string, GateDetail>>({});
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [routerChoice, setRouterChoice] = useState<string | null>(null);
  // EventSource ref — SSE 미사용 시 대비 예약 (현재 fetch reader 방식 사용)
  // const _esRef = useRef<EventSource | null>(null);

  const startAnalysis = useCallback(async () => {
    if (!uploadId) return;
    setStatus("running");
    setGates({ ...INITIAL_GATES, router: "running" });
    setGateDetails({});
    setError(null);
    setRouterChoice(null);

    try {
      if (file) {
        const { response } = await analyzeCsv(file);
        const meta = response.meta;
        const schemaStatus = statusFromGateValue(meta.gates["schema_gate"]);
        const domainStatus = statusFromGateValue(meta.gates["domain_gate"]);
        const critiqueStatus = statusFromGateValue(meta.gates["critique_gate"]);
        const nextGates: GateState = {
          router: "pass",
          schema: schemaStatus,
          domain: domainStatus,
          critique: critiqueStatus,
          done: false,
        };
        const directDetails: Record<string, GateDetail> = {
          router: {
            gate: "router",
            status: "pass",
            detail: meta.asset_class,
            reason: meta.router_reason,
          },
        };

        const directGateMap = [
          ["schema", schemaStatus, meta.gates["schema_gate"]],
          ["domain", domainStatus, meta.gates["domain_gate"]],
          ["critique", critiqueStatus, meta.gates["critique_gate"]],
        ] as const;

        for (const [gate, gateStatus, rawDetail] of directGateMap) {
          if (gateStatus === "pass" || gateStatus === "fail") {
            directDetails[gate] = {
              gate,
              status: gateStatus,
              detail: detailFromGateValue(rawDetail),
              reason: detailFromGateValue(rawDetail),
            };
          }
        }

        const hasFailure = [schemaStatus, domainStatus, critiqueStatus].includes("fail");
        setRouterChoice(meta.router_reason || `${meta.asset_class} analyzer`);
        setGateDetails(directDetails);
        setGates({ ...nextGates, done: !hasFailure && response.status !== "error" });

        if (hasFailure || response.status === "error") {
          setStatus("error");
          setError(
            (response.result?.["_analyzer_error"] as string | undefined) ??
              "분석 결과 검증에 실패했습니다.",
          );
          return;
        }

        setStatus("done");
        setTimeout(() => onComplete?.(), 2500);
        return;
      }

      // POST /upload/analyze → SSE stream
      const res = await fetch(`${API_BASE}/upload/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upload_id: uploadId,
          config: {
            analyzer: config.analyzer,
            period_days: config.period_days,
            base_currency: config.currency,
            include_fx: config.include_fx,
          },
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`분석 요청 실패 (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const chunk of lines) {
          if (!chunk.startsWith("data:")) continue;
          const jsonStr = chunk.replace(/^data:\s*/, "").trim();
          if (!jsonStr) continue;

          try {
            const evt = JSON.parse(jsonStr) as Record<string, unknown>;

            if (evt["type"] === "gate") {
              const gate = evt["gate"] as GateKey;
              const evtStatus = evt["status"] as "pass" | "fail";

              if (gate === "router" && evtStatus === "pass") {
                const detail = evt["detail"] as string | undefined;
                if (detail) setRouterChoice(detail);
              }

              setGateDetails((prev) => ({
                ...prev,
                [gate]: {
                  gate,
                  status: evtStatus,
                  detail: evt["detail"] as string | undefined,
                  reason: evt["reason"] as string | undefined,
                },
              }));

              setGates((prev) => {
                const next = { ...prev, [gate]: evtStatus === "pass" ? "pass" : "fail" } as GateState;
                // 다음 게이트 running 상태로
                const order = ["router", "schema", "domain", "critique"] as const;
                const idx = order.indexOf(gate as (typeof order)[number]);
                if (evtStatus === "pass" && idx < order.length - 1) {
                  next[order[idx + 1]!] = "running";
                }
                return next;
              });
              if (evtStatus === "fail") {
                setStatus("error");
                setError((evt["reason"] as string | undefined) ?? (evt["detail"] as string | undefined) ?? "분석 게이트 실패");
              }
            } else if (typeof evt["step"] === "string") {
              const stepToGate: Record<string, GateKey | "complete"> = {
                router: "router",
                schema_gate: "schema",
                schema: "schema",
                domain_gate: "domain",
                domain: "domain",
                critique_gate: "critique",
                critique: "critique",
                complete: "complete",
              };
              const step = stepToGate[evt["step"]];
              const evtStatus = evt["status"] as GateStatus;
              const message = (evt["message"] as string | undefined) ?? "";

              if (step === "complete") {
                if (evtStatus === "pass") {
                  setGates((prev) => ({ ...prev, done: true }));
                  setStatus("done");
                  setTimeout(() => onComplete?.(), 2500);
                }
                continue;
              }

              if (!step) continue;

              if (step === "router" && evtStatus === "pass" && message) {
                setRouterChoice(message);
              }

              if (evtStatus === "pass" || evtStatus === "fail") {
                setGateDetails((prev) => ({
                  ...prev,
                  [step]: {
                    gate: step,
                    status: evtStatus,
                    detail: message,
                    reason: message,
                  },
                }));
              }

              setGates((prev) => {
                const next = { ...prev, [step]: evtStatus } as GateState;
                const order = ["router", "schema", "domain", "critique"] as const;
                const idx = order.indexOf(step);
                if (evtStatus === "pass" && idx < order.length - 1) {
                  next[order[idx + 1]!] = "running";
                }
                return next;
              });

              if (evtStatus === "fail") {
                setStatus("error");
                setError(message || "분석 게이트 실패");
              }
            } else if (evt["type"] === "done") {
              setGates((prev) => ({ ...prev, done: true }));
              setStatus("done");
              // 3초 후 대시보드 리다이렉트
              setTimeout(() => onComplete?.(), 2500);
            } else if (evt["type"] === "error") {
              throw new Error((evt["message"] as string) ?? "분석 중 오류");
            }
          } catch {
            // JSON parse 오류 무시
          }
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "알 수 없는 오류";
      setError(msg);
      setStatus("error");
    }
  }, [uploadId, file, config, onComplete]);

  const gateOrder = ["router", "schema", "domain", "critique"] as const;

  return (
    <Card data-testid="analyze-progress-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{t("upload.section.progress")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Router 선택 배지 */}
        {routerChoice && (
          <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs">
            <span className="rounded bg-primary px-1.5 py-0.5 text-xs font-semibold text-primary-foreground">
              Router
            </span>
            <span className="text-muted-foreground">{routerChoice}</span>
          </div>
        )}

        {/* 게이트 배지 */}
        <div className="space-y-2" data-testid="gate-badges">
          {gateOrder.map((gate, idx) => {
            const s = gates[gate];
            const detail = gateDetails[gate];
            return (
              <div
                key={gate}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors",
                  s === "pass"
                    ? "border-green-500/30 bg-green-500/10"
                    : s === "fail"
                      ? "border-destructive/30 bg-destructive/10"
                      : s === "running"
                        ? "border-primary/30 bg-primary/5"
                        : "border-border bg-muted/20",
                )}
                data-gate={gate}
                data-status={s}
              >
                {s === "pass" ? (
                  <CheckCircle className="h-4 w-4 shrink-0 text-green-500" aria-label={t("upload.gate.pass")} />
                ) : s === "fail" ? (
                  <AlertCircle className="h-4 w-4 shrink-0 text-destructive" aria-label={t("upload.gate.fail")} />
                ) : s === "running" ? (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-label={t("upload.gate.running")} />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted-foreground/40" aria-label={t("upload.gate.idle")} />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-xs font-semibold",
                        s === "pass"
                          ? "text-green-500"
                          : s === "fail"
                            ? "text-destructive"
                            : s === "running"
                              ? "text-primary"
                              : "text-muted-foreground/60",
                      )}
                    >
                      {idx + 1}. {GATE_LABELS[gate]}
                    </span>
                    {s === "pass" && (
                      <span className="rounded bg-green-500/20 px-1 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-400">
                        PASS
                      </span>
                    )}
                  </div>
                  {detail?.reason && (
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      {detail.reason}
                    </p>
                  )}
                </div>
                {s === "running" && (
                  <ChevronRight className="h-3 w-3 shrink-0 animate-pulse text-primary" aria-hidden="true" />
                )}
              </div>
            );
          })}
        </div>

        {/* 완료 메시지 */}
        {status === "done" && (
          <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-xs text-green-600 dark:text-green-400">
            <CheckCircle className="h-4 w-4" aria-hidden="true" />
            {t("upload.analyze.complete")}
          </div>
        )}

        {/* 에러 */}
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}

        {/* 분석 시작 버튼 */}
        <Button
          className="w-full"
          onClick={startAnalysis}
          disabled={disabled || !uploadId || status === "running" || status === "done"}
          data-testid="start-analyze-btn"
        >
          {status === "running" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              {t("upload.analyze.running")}
            </>
          ) : status === "done" ? (
            <>
              <CheckCircle className="mr-2 h-4 w-4" aria-hidden="true" />
              {t("upload.analyze.done")}
            </>
          ) : (
            t("upload.analyze.start")
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
