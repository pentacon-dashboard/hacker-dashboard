"use client";

import { FormEvent, useRef } from "react";
import { Send, Loader2, Bot, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardRenderer } from "@/components/copilot/cards";
import type { CopilotStreamState, StepState } from "@/hooks/use-copilot-stream";
import { useLocale } from "@/lib/i18n/locale-provider";

interface ThreadMessage {
  role: "user" | "assistant";
  content: string;
  turn_id?: string;
  analyzer?: string;
  analyzer_reason?: string;
}

interface ThreadViewProps {
  sessionId?: string | null;
  messages?: ThreadMessage[];
  streamState: CopilotStreamState;
  onSendMessage: (query: string) => void;
  disabled?: boolean;
}

export function ThreadView({
  sessionId,
  messages = [],
  streamState,
  onSendMessage,
  disabled,
}: ThreadViewProps) {
  const { t } = useLocale();
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const val = inputRef.current?.value.trim();
    if (!val) return;
    onSendMessage(val);
    if (inputRef.current) inputRef.current.value = "";
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  }

  const stepEntries = Object.entries(streamState.steps) as [string, StepState][];
  const isStreaming = streamState.status === "streaming";

  return (
    <div className="flex h-full flex-col" data-testid="thread-view">
      {/* 스레드 스크롤 영역 */}
      <div className="flex-1 space-y-4 overflow-y-auto px-1 py-2">
        {/* 세션 없음 / 빈 상태 */}
        {!sessionId && messages.length === 0 && streamState.status === "idle" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Bot className="mb-3 h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="text-sm font-medium text-muted-foreground">{t("copilot.emptyTitle")}</p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              {t("copilot.emptyDesc")}
            </p>
          </div>
        )}

        {/* 기존 메시지 히스토리 */}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            <div
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                msg.role === "user" ? "bg-primary" : "bg-muted"
              }`}
            >
              {msg.role === "user" ? (
                <User className="h-3.5 w-3.5 text-primary-foreground" aria-hidden="true" />
              ) : (
                <Bot className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              )}
            </div>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "border border-border bg-card"
              }`}
            >
              {/* Analyzer 배지 */}
              {msg.analyzer && (
                <div className="mb-1.5 flex items-center gap-1.5">
                  <span className="rounded bg-primary/20 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                    Router: {msg.analyzer}
                  </span>
                  {msg.analyzer_reason && (
                    <span className="text-[10px] text-muted-foreground">{msg.analyzer_reason}</span>
                  )}
                </div>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* 실시간 스트리밍 */}
        {isStreaming && (
          <div className="space-y-3">
            {/* Plan 배지 */}
            {streamState.plan && (
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-muted-foreground">
                <span className="font-semibold text-primary">Plan:</span> {streamState.plan.plan_id} &middot;{" "}
                {streamState.plan.steps.length}단계
              </div>
            )}

            {stepEntries.map(([stepId, stepState]) => (
              <div key={stepId} className="space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
                  <span className="font-mono">{stepId}</span>
                  {stepState.degraded && (
                    <span className="rounded bg-destructive/10 px-1 py-0.5 text-[10px] text-destructive">
                      {t("copilot.degraded")}
                    </span>
                  )}
                </div>

                {!stepState.card && stepState.buffer && (
                  <div
                    className="rounded border border-border bg-card px-3 py-2 text-sm text-muted-foreground"
                    aria-live="polite"
                  >
                    {stepState.buffer}
                    <span className="animate-pulse">|</span>
                  </div>
                )}

                {!stepState.card && !stepState.buffer && (
                  <div className="h-14 animate-pulse rounded border border-border bg-muted" aria-label={t("copilot.loading")} />
                )}

                {stepState.card && (
                  <CardRenderer card={stepState.card} stepId={stepId} />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Final 카드 */}
        {streamState.finalCard && (
          <div className="space-y-1" data-testid="final-card">
            <div className="text-xs font-semibold text-muted-foreground">{t("copilot.finalResponse")}</div>
            <CardRenderer card={streamState.finalCard} suppressDegradedBanner />
          </div>
        )}

        {/* 에러 */}
        {streamState.error && (
          <div className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {t("copilot.error")}: {streamState.error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 입력 폼 */}
      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border pt-3">
        <input
          ref={inputRef}
          type="text"
          placeholder={t("copilot.inputPlaceholder")}
          disabled={disabled || isStreaming}
          className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
          aria-label={t("copilot.inputAria")}
          data-testid="thread-input"
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || isStreaming}
          aria-label={t("copilot.send")}
          data-testid="thread-send-btn"
        >
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </form>
    </div>
  );
}
