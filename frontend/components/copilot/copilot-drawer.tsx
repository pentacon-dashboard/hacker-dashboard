"use client";

import { useEffect } from "react";
import type { CopilotStreamState, StepState } from "@/hooks/use-copilot-stream";
import { CardRenderer } from "./cards";

interface CopilotDrawerProps {
  open: boolean;
  onClose: () => void;
  state: CopilotStreamState;
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
          <h2 className="text-sm font-semibold">Copilot 분석</h2>
          <button
            onClick={onClose}
            aria-label="닫기"
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
            <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              Plan: {state.plan.plan_id} · {state.plan.steps.length}개 step
            </div>
          )}

          {/* Step별 카드 */}
          {stepEntries.map(([stepId, stepState]) => (
            <div key={stepId} className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <span className="font-mono">{stepId}</span>
                {stepState.degraded && (
                  <span className="rounded bg-destructive/10 px-1 text-destructive text-[10px]">
                    품질저하
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
                <div className="h-16 rounded border bg-muted animate-pulse" aria-label="로딩 중" />
              )}

              {/* 카드 swap — step.result 수신 후 */}
              {stepState.card && (
                <CardRenderer card={stepState.card} stepId={stepId} />
              )}
            </div>
          ))}

          {/* Final 카드 */}
          {state.finalCard && (
            <div className="space-y-1" data-testid="copilot-card-final">
              <div className="text-xs font-semibold text-muted-foreground">통합 응답</div>
              {/* Final card 는 step 카드에서 이미 degraded 배너를 표시했으므로 중복 방지 */}
              <CardRenderer card={state.finalCard} suppressDegradedBanner />
            </div>
          )}

          {/* 에러 */}
          {state.error && (
            <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              오류: {state.error}
            </div>
          )}

          {/* 완료 */}
          {state.status === "completed" && state.turnId && (
            <div className="text-xs text-muted-foreground text-right">
              Turn: {state.turnId}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
