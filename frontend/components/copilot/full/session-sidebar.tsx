"use client";

import { useState } from "react";
import { Search, Plus, MessageSquare, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CopilotSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turn_count: number;
  last_query?: string;
}

interface SessionSidebarProps {
  sessions: CopilotSession[];
  activeSessionId?: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  loading?: boolean;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return "오늘";
    if (diffDays === 1) return "어제";
    if (diffDays < 7) return `${diffDays}일 전`;
    return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  loading,
}: SessionSidebarProps) {
  const [query, setQuery] = useState("");

  const filtered = sessions.filter(
    (s) =>
      s.title.toLowerCase().includes(query.toLowerCase()) ||
      (s.last_query ?? "").toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="flex h-full flex-col gap-3" data-testid="session-sidebar">
      {/* 새 세션 버튼 */}
      <button
        onClick={onNewSession}
        className="flex w-full items-center gap-2 rounded-lg border border-dashed border-primary/40 bg-primary/5 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
        data-testid="new-session-btn"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        새 대화 시작
      </button>

      {/* 검색 */}
      <div className="relative">
        <Search
          className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          type="text"
          placeholder="대화 검색..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-md border border-input bg-background py-1.5 pl-7 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          aria-label="세션 검색"
        />
      </div>

      {/* 세션 목록 */}
      <div className="flex-1 space-y-1 overflow-y-auto" role="list" aria-label="대화 목록">
        {loading && (
          <div className="space-y-1.5">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg border border-border bg-muted/20" />
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="py-8 text-center text-xs text-muted-foreground">
            {query ? "검색 결과가 없습니다" : "대화 기록이 없습니다"}
          </div>
        )}

        {!loading &&
          filtered.map((session) => (
            <button
              key={session.session_id}
              role="listitem"
              onClick={() => onSelectSession(session.session_id)}
              className={cn(
                "flex w-full flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left transition-colors",
                activeSessionId === session.session_id
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/40 hover:bg-muted/40",
              )}
              aria-pressed={activeSessionId === session.session_id}
              data-testid={`session-item-${session.session_id}`}
            >
              <div className="flex w-full items-center justify-between gap-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <MessageSquare className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="truncate text-xs font-medium">{session.title}</span>
                </div>
                <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/50" aria-hidden="true" />
              </div>
              {session.last_query && (
                <p className="truncate pl-4 text-xs text-muted-foreground">{session.last_query}</p>
              )}
              <div className="flex items-center gap-2 pl-4">
                <span className="text-[10px] text-muted-foreground/60">
                  {formatDate(session.updated_at)}
                </span>
                <span className="text-[10px] text-muted-foreground/60">
                  {session.turn_count}턴
                </span>
              </div>
            </button>
          ))}
      </div>
    </div>
  );
}
