"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, MessageSquare, PanelLeftClose, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

export interface CopilotSession {
  session_id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
  last_turn_at?: string;
  turn_count: number;
  last_query?: string;
  preview?: string;
}

interface SessionSidebarProps {
  sessions: CopilotSession[];
  activeSessionId?: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  loading?: boolean;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  loading,
  collapsed = false,
  onToggleCollapsed,
}: SessionSidebarProps) {
  const { t, locale } = useLocale();
  const [query, setQuery] = useState("");

  function formatDate(session: CopilotSession): string {
    const iso = session.updated_at ?? session.last_turn_at ?? session.created_at ?? "";
    if (!iso) return "";
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffDays = Math.floor(diffMs / 86400000);
      if (diffDays === 0) return t("copilot.today");
      if (diffDays === 1) return t("copilot.yesterday");
      if (diffDays < 7) return t("copilot.daysAgo", { n: diffDays });
      return d.toLocaleDateString(locale === "en" ? "en-US" : "ko-KR", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return iso;
    }
  }

  const filtered = sessions.filter((session) => {
    const preview = session.last_query ?? session.preview ?? "";
    return (
      session.title.toLowerCase().includes(query.toLowerCase()) ||
      preview.toLowerCase().includes(query.toLowerCase())
    );
  });

  if (collapsed) {
    return (
      <div
        className="flex h-full w-14 flex-col items-center gap-2 border-r border-border bg-muted/20 px-2 py-3"
        data-testid="session-sidebar"
        data-collapsed="true"
      >
        <Button
          type="button"
          size="icon"
          variant="ghost"
          onClick={onToggleCollapsed}
          aria-label="사이드바 펼치기"
          data-testid="sidebar-collapse-btn"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
        <Button
          type="button"
          size="icon"
          onClick={onNewSession}
          aria-label={t("copilot.newChat")}
          data-testid="new-session-btn"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
        </Button>
        <div className="mt-2 flex flex-col gap-1">
          {sessions.slice(0, 8).map((session) => (
            <button
              key={session.session_id}
              type="button"
              onClick={() => onSelectSession(session.session_id)}
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground",
                activeSessionId === session.session_id && "bg-primary/10 text-primary",
              )}
              aria-label={session.title}
            >
              <MessageSquare className="h-4 w-4" aria-hidden="true" />
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-muted/20"
      data-testid="session-sidebar"
      data-collapsed="false"
    >
      <div className="flex items-center justify-between border-b border-border px-3 py-3">
        <span className="text-sm font-semibold">Copilot</span>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          onClick={onToggleCollapsed}
          aria-label="사이드바 접기"
          data-testid="sidebar-collapse-btn"
        >
          <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      <div className="space-y-3 px-3 py-3">
        <Button
          type="button"
          onClick={onNewSession}
          className="w-full justify-start gap-2"
          data-testid="new-session-btn"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t("copilot.newChat")}
        </Button>

        <div className="relative">
          <Search
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="text"
            placeholder={t("copilot.searchSessions")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-md border border-input bg-background py-2 pl-8 pr-3 text-sm outline-none focus:ring-1 focus:ring-ring"
            aria-label={t("copilot.searchSessions")}
          />
        </div>
      </div>

      <div
        className="flex-1 space-y-1 overflow-y-auto px-2 pb-3"
        role="list"
        aria-label={t("copilot.sessionList")}
      >
        {loading && (
          <div className="space-y-2 px-1">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            {query ? t("copilot.noSessionsSearch") : t("copilot.noSessions")}
          </div>
        )}

        {!loading &&
          filtered.map((session) => {
            const preview = session.last_query ?? session.preview ?? "";
            return (
              <button
                key={session.session_id}
                role="listitem"
                type="button"
                onClick={() => onSelectSession(session.session_id)}
                className={cn(
                  "group flex w-full flex-col items-start gap-1 rounded-md px-3 py-2 text-left transition-colors",
                  activeSessionId === session.session_id
                    ? "bg-primary/10 text-foreground"
                    : "hover:bg-muted",
                )}
                aria-pressed={activeSessionId === session.session_id}
                data-testid={`session-item-${session.session_id}`}
              >
                <div className="flex w-full items-center gap-2">
                  <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{session.title}</span>
                  <ChevronLeft className="h-3 w-3 shrink-0 rotate-180 text-muted-foreground/40 opacity-0 group-hover:opacity-100" />
                </div>
                {preview && <p className="line-clamp-2 pl-6 text-xs text-muted-foreground">{preview}</p>}
                <div className="flex items-center gap-2 pl-6 text-[11px] text-muted-foreground/70">
                  <span>{formatDate(session)}</span>
                  <span>{t("copilot.turns", { n: session.turn_count })}</span>
                </div>
              </button>
            );
          })}
      </div>
    </div>
  );
}
