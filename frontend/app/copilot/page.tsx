"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SessionSidebar, type CopilotSession } from "@/components/copilot/full/session-sidebar";
import { ThreadView } from "@/components/copilot/full/thread-view";
import { ReferencePanel } from "@/components/copilot/full/reference-panel";
import { useCopilotStream, type CopilotCard } from "@/hooks/use-copilot-stream";
import { API_BASE } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/locale-provider";

// TODO: BE γ-sprint 완료 후 실 엔드포인트로 swap (현재 MSW stub 사용)
async function fetchSessions(): Promise<CopilotSession[]> {
  try {
    const res = await fetch(`${API_BASE}/copilot/sessions`);
    if (!res.ok) return [];
    return res.json() as Promise<CopilotSession[]>;
  } catch {
    return [];
  }
}

interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  turn_id?: string;
  analyzer?: string;
  analyzer_reason?: string;
}

function finalCardToMessage(card: CopilotCard | null): string {
  if (!card) return "";
  if (typeof card.content === "string" && card.content.trim()) return normalizeAssistantText(card.content);
  if (typeof card.body === "string" && card.body.trim()) return normalizeAssistantText(card.body);
  return "분석 결과를 정리했습니다.";
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function normalizeAssistantText(text: string): string {
  let cleaned = text.trim();
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim();

  try {
    const parsed = JSON.parse(cleaned) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      const data = parsed as Record<string, unknown>;
      for (const key of ["answer", "response", "content", "summary", "message", "analysis"]) {
        const value = data[key];
        if (typeof value === "string" && value.trim()) return value.trim();
      }
      const lines = Object.entries(data)
        .filter(([key]) => !["type", "metadata"].includes(key))
        .slice(0, 6)
        .map(([key, value]) => `${key.replace(/_/g, " ")}: ${formatValue(value)}`);
      if (lines.length) return lines.join("\n");
    }
    if (Array.isArray(parsed)) {
      const lines = parsed.slice(0, 6).map((item) => `- ${formatValue(item)}`);
      if (lines.length) return lines.join("\n");
    }
  } catch {
    // Plain text is the normal path.
  }

  cleaned = cleaned.replace(/^\[[^\]]+\]\s*/gm, "");
  cleaned = cleaned.replace(/\s*\((?:sync fallback|degraded)\)\s*/gi, " ");
  cleaned = cleaned.replace(/(?:stock|crypto|fx|macro|portfolio|rebalance|포트폴리오)\s*분석\s*결과\s*:\s*/gi, "");
  cleaned = cleaned.replace(/sync fallback\s*:\s*/gi, "");

  return cleaned.trim() || "분석 결과를 정리했습니다.";
}

export default function CopilotPage() {
  const { t } = useLocale();
  const [sessions, setSessions] = useState<CopilotSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [historyMessages, setHistoryMessages] = useState<HistoryMessage[]>([]);
  const [liveMessages, setLiveMessages] = useState<HistoryMessage[]>([]);
  const appendedTurnRef = useRef<string | null>(null);

  const { state: streamState, query: sendQuery, reset } = useCopilotStream();

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      setSessionsLoading(false);
    });
  }, []);

  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setActiveSessionId(sessionId);
      reset();
      setHistoryMessages([]);
      setLiveMessages([]);
      appendedTurnRef.current = null;

      // TODO: BE γ-sprint — 세션 상세 페치
      try {
        const res = await fetch(`${API_BASE}/copilot/sessions/${sessionId}`);
        if (!res.ok) return;
        const data = (await res.json()) as {
          turns?: Array<{
            query?: string;
            final_card?: { content?: string; body?: string };
            analyzer?: string;
            analyzer_reason?: string;
            turn_id?: string;
          }>;
        };
        const msgs: HistoryMessage[] = [];
        for (const turn of data.turns ?? []) {
          msgs.push({ role: "user", content: turn.query ?? "" });
          const card = turn.final_card;
          if (card) {
            msgs.push({
              role: "assistant",
              content: normalizeAssistantText((card.content ?? card.body ?? "") as string),
              analyzer: turn.analyzer,
              analyzer_reason: turn.analyzer_reason,
              turn_id: turn.turn_id,
            });
          }
        }
        setHistoryMessages(msgs);
      } catch {
        // 실패 시 빈 상태 유지
      }
    },
    [reset],
  );

  const handleNewSession = useCallback(() => {
    setActiveSessionId(null);
    reset();
    setHistoryMessages([]);
    setLiveMessages([]);
    appendedTurnRef.current = null;
  }, [reset]);

  const handleSendMessage = useCallback(
    (q: string) => {
      appendedTurnRef.current = null;
      setLiveMessages((prev) => [...prev, { role: "user", content: q }]);
      sendQuery(q, activeSessionId ?? undefined);
    },
    [sendQuery, activeSessionId],
  );

  const handleQuickQuestion = useCallback(
    (q: string) => {
      appendedTurnRef.current = null;
      setLiveMessages((prev) => [...prev, { role: "user", content: q }]);
      sendQuery(q, activeSessionId ?? undefined);
    },
    [sendQuery, activeSessionId],
  );

  useEffect(() => {
    if (streamState.status !== "completed" || !streamState.finalCard || !streamState.turnId) return;
    if (appendedTurnRef.current === streamState.turnId) return;

    appendedTurnRef.current = streamState.turnId;
    setLiveMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: finalCardToMessage(streamState.finalCard),
        turn_id: streamState.turnId ?? undefined,
      },
    ]);
    if (streamState.sessionId) setActiveSessionId(streamState.sessionId);
    fetchSessions().then(setSessions);
  }, [streamState.status, streamState.finalCard, streamState.turnId, streamState.sessionId]);

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          {t("copilot.title")}
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
            Beta
          </span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("copilot.subtitle")}</p>
      </div>

      {/* 3 컬럼 레이아웃 */}
      <div
        className="grid h-[calc(100vh-200px)] min-h-[500px] grid-cols-1 gap-4 md:grid-cols-12"
        data-testid="copilot-layout"
      >
        {/* 좌: 세션 사이드바 (3/12) */}
        <div className="overflow-hidden rounded-xl border border-border bg-card p-3 md:col-span-3">
          <SessionSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onNewSession={handleNewSession}
            loading={sessionsLoading}
          />
        </div>

        {/* 중앙: 대화 스레드 (6/12) */}
        <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-card p-3 md:col-span-6">
          <ThreadView
            sessionId={activeSessionId}
            messages={[...historyMessages, ...liveMessages]}
            streamState={streamState}
            onSendMessage={handleSendMessage}
            disabled={false}
          />
        </div>

        {/* 우: 레퍼런스 패널 (3/12) */}
        <div className="overflow-hidden rounded-xl border border-border bg-card p-3 md:col-span-3">
          <ReferencePanel onQuickQuestion={handleQuickQuestion} />
        </div>
      </div>
    </div>
  );
}
