"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  SessionSidebar,
  type CopilotSession,
} from "@/components/copilot/full/session-sidebar";
import { ThreadView } from "@/components/copilot/full/thread-view";
import {
  ArtifactPanel,
  ArtifactRail,
  hasArtifacts,
  type ArtifactSummary,
  type ArtifactTab,
} from "@/components/copilot/full/artifact-panel";
import {
  useCopilotStream,
  type CopilotCard,
  type CopilotStreamState,
} from "@/hooks/use-copilot-stream";
import { API_BASE } from "@/lib/api/client";

async function fetchSessions(): Promise<CopilotSession[]> {
  try {
    const res = await fetch(`${API_BASE}/copilot/sessions`);
    if (!res.ok) return [];
    const data = (await res.json()) as Array<{
      session_id: string;
      title: string;
      last_turn_at?: string;
      updated_at?: string;
      turn_count: number;
      preview?: string;
      last_query?: string;
    }>;
    return data.map((session) => ({
      ...session,
      updated_at: session.updated_at ?? session.last_turn_at,
      last_query: session.last_query ?? session.preview,
    }));
  } catch {
    return [];
  }
}

interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  card?: CopilotCard;
  turn_id?: string;
  analyzer?: string;
  analyzer_reason?: string;
  degraded?: boolean;
  artifacts?: ArtifactSummary;
}

function finalCardToMessage(card: CopilotCard | null): string {
  if (!card) return "";
  if (typeof card.content === "string" && card.content.trim()) {
    return normalizeAssistantText(card.content);
  }
  if (typeof card.body === "string" && card.body.trim()) {
    return normalizeAssistantText(card.body);
  }
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
  cleaned = cleaned.replace(
    /(?:stock|crypto|fx|macro|portfolio|rebalance)\s*analysis\s*:\s*/gi,
    "",
  );
  cleaned = cleaned.replace(/sync fallback\s*:\s*/gi, "");

  return cleaned.trim() || "분석 결과를 정리했습니다.";
}

function addArtifact(summary: ArtifactSummary, key: ArtifactTab, count = 1) {
  summary[key] = Number(summary[key] ?? 0) + count;
}

function artifactSummaryFromCard(card?: CopilotCard | null): ArtifactSummary {
  const summary: ArtifactSummary = {};
  if (!card) return summary;

  if (Array.isArray(card.citations)) addArtifact(summary, "citations", card.citations.length);

  switch (card.type) {
    case "citation":
    case "news_rag_list":
      addArtifact(summary, "citations");
      break;
    case "chart":
      addArtifact(summary, "charts");
      break;
    case "comparison_table":
    case "scorecard":
      addArtifact(summary, "data");
      break;
    case "simulator_result":
      addArtifact(summary, "actions");
      break;
    default:
      break;
  }
  return summary;
}

function mergeArtifactSummary(items: ArtifactSummary[]): ArtifactSummary {
  return items.reduce<ArtifactSummary>((acc, item) => {
    for (const key of ["citations", "charts", "data", "actions"] as ArtifactTab[]) {
      if (item[key]) addArtifact(acc, key, Number(item[key]));
    }
    return acc;
  }, {});
}

function artifactSummaryFromStream(streamState: CopilotStreamState): ArtifactSummary {
  const stepSummaries = Object.values(streamState.steps).map((step) =>
    artifactSummaryFromCard(step.card),
  );
  return mergeArtifactSummary([...stepSummaries, artifactSummaryFromCard(streamState.finalCard)]);
}

export default function CopilotPage() {
  const [sessions, setSessions] = useState<CopilotSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [historyMessages, setHistoryMessages] = useState<HistoryMessage[]>([]);
  const [liveMessages, setLiveMessages] = useState<HistoryMessage[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [artifactOpen, setArtifactOpen] = useState(false);
  const [activeArtifactTab, setActiveArtifactTab] = useState<ArtifactTab>("citations");
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
      setMobileSidebarOpen(false);
      setActiveSessionId(sessionId);
      reset();
      setHistoryMessages([]);
      setLiveMessages([]);
      setArtifactOpen(false);
      appendedTurnRef.current = null;

      try {
        const res = await fetch(`${API_BASE}/copilot/sessions/${sessionId}`);
        if (!res.ok) return;
        const data = (await res.json()) as {
          turns?: Array<{
            query?: string;
            final_card?: CopilotCard;
            citations?: Array<unknown>;
            analyzer?: string;
            analyzer_reason?: string;
            turn_id?: string;
          }>;
        };
        const messages: HistoryMessage[] = [];
        for (const turn of data.turns ?? []) {
          messages.push({ role: "user", content: turn.query ?? "" });
          const card = turn.final_card;
          if (card) {
            const artifacts = mergeArtifactSummary([
              artifactSummaryFromCard(card),
              { citations: turn.citations?.length ?? 0 },
            ]);
            messages.push({
              role: "assistant",
              content: finalCardToMessage(card),
              card,
              analyzer: turn.analyzer,
              analyzer_reason: turn.analyzer_reason,
              turn_id: turn.turn_id,
              degraded: card.degraded === true,
              artifacts: hasArtifacts(artifacts) ? artifacts : undefined,
            });
          }
        }
        setHistoryMessages(messages);
      } catch {
        // Keep the thread empty when the session fetch fails.
      }
    },
    [reset],
  );

  const handleNewSession = useCallback(() => {
    setMobileSidebarOpen(false);
    setActiveSessionId(null);
    reset();
    setHistoryMessages([]);
    setLiveMessages([]);
    setArtifactOpen(false);
    appendedTurnRef.current = null;
  }, [reset]);

  const handleSendMessage = useCallback(
    (queryText: string) => {
      appendedTurnRef.current = null;
      setLiveMessages((prev) => [...prev, { role: "user", content: queryText }]);
      sendQuery(queryText, activeSessionId ?? undefined);
    },
    [sendQuery, activeSessionId],
  );

  const handleClientCandidateSelect = useCallback(
    (clientId: string) => {
      handleSendMessage(`${clientId} 포트폴리오 요약`);
    },
    [handleSendMessage],
  );

  useEffect(() => {
    if (streamState.status !== "completed" || !streamState.finalCard || !streamState.turnId) return;
    if (appendedTurnRef.current === streamState.turnId) return;

    const finalCard = streamState.finalCard;
    const artifacts = artifactSummaryFromStream(streamState);
    appendedTurnRef.current = streamState.turnId;
    setLiveMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: finalCardToMessage(finalCard),
        card: finalCard,
        turn_id: streamState.turnId ?? undefined,
        degraded: finalCard.degraded === true,
        artifacts: hasArtifacts(artifacts) ? artifacts : undefined,
      },
    ]);
    if (streamState.sessionId) setActiveSessionId(streamState.sessionId);
    fetchSessions().then(setSessions);
  }, [streamState]);

  const messages = useMemo(
    () => [...historyMessages, ...liveMessages],
    [historyMessages, liveMessages],
  );

  const visibleArtifacts = useMemo(() => {
    const streamingArtifacts = artifactSummaryFromStream(streamState);
    if (hasArtifacts(streamingArtifacts)) return streamingArtifacts;
    const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
    return lastAssistant?.artifacts ?? {};
  }, [messages, streamState]);

  const openArtifactPanel = useCallback((tab: ArtifactTab) => {
    setActiveArtifactTab(tab);
    setArtifactOpen(true);
  }, []);

  return (
    <div className="relative flex h-[calc(100vh-96px)] min-h-[620px] overflow-hidden rounded-lg border border-border bg-background">
      <div className="hidden h-full md:flex">
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          loading={sessionsLoading}
          collapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed((value) => !value)}
        />
      </div>

      <div className="flex h-full md:hidden">
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          loading={sessionsLoading}
          collapsed
          onToggleCollapsed={() => setMobileSidebarOpen(true)}
        />
      </div>

      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-50 flex md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Copilot sessions"
        >
          <button
            type="button"
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            aria-label="Close sessions drawer"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative h-full shadow-xl">
            <SessionSidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectSession={handleSelectSession}
              onNewSession={handleNewSession}
              loading={sessionsLoading}
              collapsed={false}
              onToggleCollapsed={() => setMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      <main className="min-w-0 flex-1">
        <ThreadView
          sessionId={activeSessionId}
          messages={messages}
          streamState={streamState}
          onSendMessage={handleSendMessage}
          onClientCandidateSelect={handleClientCandidateSelect}
          onArtifactSelect={openArtifactPanel}
        />
      </main>

      {!artifactOpen && hasArtifacts(visibleArtifacts) && (
        <ArtifactRail summary={visibleArtifacts} onOpen={openArtifactPanel} />
      )}
      {artifactOpen && hasArtifacts(visibleArtifacts) && (
        <ArtifactPanel
          summary={visibleArtifacts}
          activeTab={activeArtifactTab}
          onTabChange={setActiveArtifactTab}
          onClose={() => setArtifactOpen(false)}
        />
      )}
    </div>
  );
}
