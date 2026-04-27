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

/**
 * CopilotDrawer — 우측 오프캔버스 drawer.
 *
 * progressive 렌더:
 * - step.start → skeleton
 * - step.token → 타이핑 버퍼 (텍스트 미리보기)
 * - step.result → 카드 swap (degraded 포함)
 * - final.card → 통합 응답
 * Esc 키로 닫힘.
 */
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
      {/* 배경 오버레이 */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer 패널 */}
      <div
        role="dialog"
        aria-label="Copilot"
        aria-modal="true"
        data-testid="copilot-drawer"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col overflow-hidden border-l bg-background shadow-xl"
      >
        {/* 헤더 */}
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

        {/* 스크롤 가능 콘텐츠 */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {/* Plan 카드 */}
          {state.plan && (
            <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
              <span>질문을 이해하고 답변을 구성하고 있습니다.</span>
            </div>
          )}

          {/* Step별 카드 */}
          {stepEntries.map(([stepId, stepState]) => {
            const stepMeta = state.plan?.steps.find((step) => step.step_id === stepId);

            return (
              <div key={stepId} className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
                  <span>{agentLabel(stepMeta?.agent)} 분석 중</span>
                  {stepState.degraded && (
                    <span className="rounded bg-destructive/10 px-1 text-destructive text-[10px]">
                      일부 제한
                    </span>
                  )}
                </div>

                {/* 버퍼 (step.token 타이핑 미리보기) — card 수신 전까지만 표시 */}
                {!stepState.card && stepState.buffer && (
                  <div
                    className="rounded border bg-card p-3 text-sm text-muted-foreground"
                    aria-live="polite"
                  >
                    {stepState.buffer}
                    <span className="animate-pulse">|</span>
                  </div>
                )}

                {/* 스켈레톤 — 버퍼도 카드도 없으면 */}
                {!stepState.card && !stepState.buffer && (
                  <div className="h-16 rounded border bg-muted animate-pulse" aria-label={t("copilot.loading")} />
                )}

                {/* step.result 는 내부 실행 결과이므로 최종 답변 전에는 요약 상태만 보여준다. */}
                {stepState.card && !state.finalCard && (
                  <div className="rounded border bg-card p-3 text-sm text-muted-foreground">
                    분석 결과를 대화형 답변으로 정리하고 있습니다.
                  </div>
                )}
              </div>
            );
          })}

          {/* Final 카드 */}
          {state.finalCard && (
            <div className="space-y-1" data-testid="copilot-card-final">
              <div className="text-xs font-semibold text-muted-foreground">{t("copilot.finalResponse")}</div>
              {/* Final card 는 step 카드에서 이미 degraded 배너를 표시했으므로 중복 방지 */}
              <CardRenderer card={state.finalCard} suppressDegradedBanner />
            </div>
          )}

          {/* 에러 */}
          {state.error && (
            <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {t("copilot.error")}: {state.error}
            </div>
          )}

          {/* 완료 */}
          {state.status === "completed" && state.turnId && (
            <div className="text-xs text-muted-foreground text-right">
              대화가 저장되었습니다.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
