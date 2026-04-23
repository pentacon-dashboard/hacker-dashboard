"use client";

import { useCallback, useState } from "react";
import { CheckCircle, Circle, Loader2, AlertCircle, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api/client";
import type { AnalyzerConfig } from "./analyzer-config-card";

type GateStatus = "idle" | "running" | "pass" | "fail";

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

const GATE_LABELS: Record<keyof Omit<GateState, "done">, string> = {
  router: "Router 선택",
  schema: "스키마 검증",
  domain: "도메인 sanity",
  critique: "AI self-critique",
};

interface GateDetail {
  gate: string;
  status: "pass" | "fail";
  detail?: string;
  reason?: string;
}

interface AnalyzeProgressCardProps {
  uploadId?: string | null;
  config: AnalyzerConfig;
  disabled?: boolean;
  onComplete?: () => void;
}

export function AnalyzeProgressCard({
  uploadId,
  config,
  disabled,
  onComplete,
}: AnalyzeProgressCardProps) {
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
      // POST /upload/analyze → SSE stream
      const res = await fetch(`${API_BASE}/upload/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upload_id: uploadId,
          analyzer: config.analyzer,
          period_days: config.period_days,
          currency: config.currency,
          include_fx: config.include_fx,
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
              const gate = evt["gate"] as string;
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
  }, [uploadId, config, onComplete]);

  const gateOrder = ["router", "schema", "domain", "critique"] as const;

  return (
    <Card data-testid="analyze-progress-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">5. 분석 진행 상태</CardTitle>
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
                  <CheckCircle className="h-4 w-4 shrink-0 text-green-500" aria-label="통과" />
                ) : s === "fail" ? (
                  <AlertCircle className="h-4 w-4 shrink-0 text-destructive" aria-label="실패" />
                ) : s === "running" ? (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-label="진행 중" />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted-foreground/40" aria-label="대기" />
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
            분석 완료! 잠시 후 대시보드로 이동합니다...
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
              분석 중...
            </>
          ) : status === "done" ? (
            <>
              <CheckCircle className="mr-2 h-4 w-4" aria-hidden="true" />
              분석 완료
            </>
          ) : (
            "분석 시작"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
