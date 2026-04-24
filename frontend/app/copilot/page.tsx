"use client";

import { useCallback, useEffect, useState } from "react";
import { SessionSidebar, type CopilotSession } from "@/components/copilot/full/session-sidebar";
import { ThreadView } from "@/components/copilot/full/thread-view";
import { ReferencePanel } from "@/components/copilot/full/reference-panel";
import { useCopilotStream } from "@/hooks/use-copilot-stream";
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

export default function CopilotPage() {
  const { t } = useLocale();
  const [sessions, setSessions] = useState<CopilotSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [historyMessages, setHistoryMessages] = useState<HistoryMessage[]>([]);

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
              content: (card.content ?? card.body ?? "") as string,
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
  }, [reset]);

  const handleSendMessage = useCallback(
    (q: string) => {
      sendQuery(q, activeSessionId ?? undefined);
    },
    [sendQuery, activeSessionId],
  );

  const handleQuickQuestion = useCallback(
    (q: string) => {
      sendQuery(q, activeSessionId ?? undefined);
    },
    [sendQuery, activeSessionId],
  );

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
            messages={historyMessages}
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
