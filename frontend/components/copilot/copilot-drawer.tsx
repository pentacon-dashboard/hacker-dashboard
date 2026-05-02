"use client";

import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import type { CopilotStreamState, StepState } from "@/hooks/use-copilot-stream";
import { CardRenderer } from "./cards";
import { useLocale } from "@/lib/i18n/locale-provider";

interface CopilotDrawerProps {
  open: boolean;
  onClose: () => void;
  state: CopilotStreamState;
}

function agentLabel(agent?: string): string {
  switch (agent) {
    case "stock":
      return "종목";
    case "crypto":
      return "가상자산";
    case "fx":
      return "환율";
    case "macro":
      return "시장";
    case "portfolio":
      return "포트폴리오";
    case "rebalance":
      return "리밸런싱";
    case "comparison":
      return "비교";
    case "simulator":
      return "시뮬레이션";
    case "news-rag":
      return "뉴스 근거";
    default:
      return "자료";
  }
}

function visibleCard(stepId: string, stepState: StepState, state: CopilotStreamState) {
  if (!stepState.card) return null;
  return {
    ...stepState.card,
    degraded: stepState.card.degraded === true || stepState.degraded,
    degraded_reason:
      (stepState.card.degraded_reason as string | undefined) ??
      (state.degraded?.step_id === stepId ? state.degraded.reason : undefined),
  };
}

export function CopilotDrawer({ open, onClose, state }: CopilotDrawerProps) {
  const { t } = useLocale();

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const stepEntries = Object.entries(state.steps) as [string, StepState][];

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-label="Copilot"
        aria-modal="true"
        data-testid="copilot-drawer"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col overflow-hidden border-l bg-background shadow-xl"
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-sm font-semibold">{t("copilot.analysis")}</h2>
          <button
            onClick={onClose}
            aria-label={t("copilot.close")}
            className="rounded p-1 text-muted-foreground hover:bg-muted"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-3">
          {state.plan && (
            <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
              <span>질의를 분석하고 필요한 작업을 구성하고 있습니다.</span>
            </div>
          )}

          {stepEntries.map(([stepId, stepState]) => {
            const stepMeta = state.plan?.steps.find((step) => step.step_id === stepId);
            const card = visibleCard(stepId, stepState, state);

            return (
              <div key={stepId} className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
                  <span>{agentLabel(stepMeta?.agent)} 분석</span>
                  {stepState.degraded && (
                    <span className="rounded bg-destructive/10 px-1 text-[10px] text-destructive">
                      일부 제한
                    </span>
                  )}
                </div>

                {!card && stepState.buffer && (
                  <div
                    className="rounded border bg-card p-3 text-sm text-muted-foreground"
                    aria-live="polite"
                  >
                    {stepState.buffer}
                    <span className="animate-pulse">|</span>
                  </div>
                )}

                {!card && !stepState.buffer && (
                  <div
                    className="h-16 animate-pulse rounded border bg-muted"
                    aria-label={t("copilot.loading")}
                  />
                )}

                {card && <CardRenderer card={card} stepId={stepId} />}
              </div>
            );
          })}

          {state.finalCard && (
            <div className="space-y-1" data-testid="copilot-card-final">
              <div className="text-xs font-semibold text-muted-foreground">
                {t("copilot.finalResponse")}
              </div>
              <CardRenderer card={state.finalCard} suppressDegradedBanner />
            </div>
          )}

          {state.error && (
            <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {t("copilot.error")}: {state.error}
            </div>
          )}

          {state.status === "completed" && state.turnId && (
            <div className="text-right text-xs text-muted-foreground">
              대화가 저장되었습니다.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
