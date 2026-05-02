"use client";

import { FormEvent, KeyboardEvent, useRef } from "react";
import { Bot, Loader2, Send, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CopilotStreamState } from "@/hooks/use-copilot-stream";
import { cn } from "@/lib/utils";
import {
  artifactChipLabel,
  artifactTabs,
  hasArtifacts,
  type ArtifactSummary,
  type ArtifactTab,
} from "./artifact-panel";

interface ThreadMessage {
  role: "user" | "assistant";
  content: string;
  turn_id?: string;
  analyzer?: string;
  analyzer_reason?: string;
  degraded?: boolean;
  artifacts?: ArtifactSummary;
}

interface ThreadViewProps {
  sessionId?: string | null;
  messages?: ThreadMessage[];
  streamState: CopilotStreamState;
  onSendMessage: (query: string) => void;
  onArtifactSelect?: (tab: ArtifactTab) => void;
  disabled?: boolean;
}

function ArtifactChips({
  summary,
  onSelect,
}: {
  summary?: ArtifactSummary;
  onSelect?: (tab: ArtifactTab) => void;
}) {
  if (!hasArtifacts(summary)) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {artifactTabs
        .filter((tab) => Number(summary[tab] ?? 0) > 0)
        .map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onSelect?.(tab)}
            className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/50 hover:text-primary"
            data-testid={`artifact-chip-${tab}`}
          >
            {artifactChipLabel(tab, Number(summary[tab] ?? 0))}
          </button>
        ))}
    </div>
  );
}

function AssistantTyping() {
  return (
    <div className="flex justify-start" data-testid="assistant-typing">
      <div className="flex w-full max-w-3xl gap-3">
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
          <Bot className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="w-full space-y-3 py-1">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
            답변을 준비하고 있습니다
          </div>
          <div className="space-y-2">
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-3 w-full animate-pulse rounded bg-muted" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function ThreadView({
  sessionId,
  messages = [],
  streamState,
  onSendMessage,
  onArtifactSelect,
  disabled,
}: ThreadViewProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isStreaming = streamState.status === "streaming";

  function submitCurrentValue() {
    const value = inputRef.current?.value.trim();
    if (!value) return;
    onSendMessage(value);
    if (inputRef.current) inputRef.current.value = "";
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submitCurrentValue();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitCurrentValue();
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-background" data-testid="thread-view">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {!sessionId && messages.length === 0 && streamState.status === "idle" && (
            <div className="flex min-h-[45vh] flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-6 w-6 text-primary" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-semibold">Copilot과 대화하기</h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                포트폴리오 요약, 리밸런싱 근거, 고객 설명 문안을 이어서 물어볼 수 있습니다.
              </p>
            </div>
          )}

          {messages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={`${msg.role}-${index}-${msg.turn_id ?? ""}`}
                className={cn("flex", isUser ? "justify-end" : "justify-start")}
                data-testid={`message-${msg.role}-${index}`}
              >
                {isUser ? (
                  <div className="max-w-[78%] rounded-2xl bg-primary px-4 py-2 text-sm leading-6 text-primary-foreground">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ) : (
                  <div className="flex w-full max-w-3xl gap-3">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                      <Bot className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex-1 text-sm leading-6">
                      {msg.degraded && (
                        <span className="mb-2 inline-flex rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-600">
                          일부 근거 제한
                        </span>
                      )}
                      <p className="whitespace-pre-wrap text-foreground">{msg.content}</p>
                      <ArtifactChips summary={msg.artifacts} onSelect={onArtifactSelect} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {isStreaming && <AssistantTyping />}
          {streamState.error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              오류: {streamState.error}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-border bg-background px-4 py-3"
        data-testid="thread-composer"
        data-multiline="true"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-input bg-background px-3 py-2 shadow-sm">
          <User className="mb-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <textarea
            ref={inputRef}
            rows={1}
            placeholder="메시지를 입력하세요"
            disabled={disabled || isStreaming}
            onKeyDown={handleKeyDown}
            className="max-h-32 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm leading-5 outline-none disabled:opacity-50"
            aria-label="질문 입력"
            data-testid="thread-input"
          />
          <Button
            type="submit"
            size="icon"
            disabled={disabled || isStreaming}
            aria-label="전송"
            data-testid="thread-send-btn"
            className="h-9 w-9 shrink-0 rounded-full"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
