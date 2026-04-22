"use client";

import React from "react";

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export interface SessionTurnCard {
  type: string;
  body?: string;
  content?: string;
  summary?: string;
  [key: string]: unknown;
}

export interface SessionTurnItem {
  turn_id: string;
  query: string;
  plan_id: string | null;
  final_card: SessionTurnCard | null;
  citations: unknown[];
  created_at: string;
}

interface TurnHistoryProps {
  /** SessionTurn 배열 — 시간 역순으로 렌더한다. */
  turns: SessionTurnItem[];
  /** 선택된 턴 ID (옵션) */
  selectedTurnId?: string | null;
  /** 턴 클릭 핸들러 (옵션) */
  onTurnClick?: (turn: SessionTurnItem) => void;
}

// ── 유틸 ─────────────────────────────────────────────────────────────────────

function _formatDate(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return isoStr;
  }
}

function _getCardText(card: SessionTurnCard | null): string {
  if (!card) return "";
  return (card.content ?? card.body ?? card.summary ?? "") as string;
}

// ── 컴포넌트 ─────────────────────────────────────────────────────────────────

/**
 * TurnHistory — 세션 턴 히스토리를 시간 역순으로 렌더한다.
 *
 * sprint-05 AC-05-9: SessionTurn 배열을 시간 역순(최신→오래된) 순으로 렌더.
 * 각 항목은 `<li>` role="listitem" 으로 렌더된다.
 */
export function TurnHistory({ turns, selectedTurnId, onTurnClick }: TurnHistoryProps) {
  // 시간 역순 정렬 (created_at 기준 — 배열을 직접 변경하지 않도록 slice)
  const sorted = [...turns].sort((a, b) => {
    return b.created_at.localeCompare(a.created_at);
  });

  if (sorted.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4 text-center">
        이전 대화가 없습니다.
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2 py-2" aria-label="이전 대화 목록">
      {sorted.map((turn) => {
        const isSelected = turn.turn_id === selectedTurnId;
        const cardText = _getCardText(turn.final_card);

        return (
          <li
            key={turn.turn_id}
            role="listitem"
            className={[
              "rounded-lg border p-3 cursor-pointer transition-colors",
              isSelected
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/40 hover:bg-muted/40",
            ].join(" ")}
            onClick={() => onTurnClick?.(turn)}
          >
            {/* 질의 */}
            <p className="font-medium text-sm truncate">{turn.query}</p>

            {/* 카드 요약 */}
            {cardText && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {cardText}
              </p>
            )}

            {/* 타임스탬프 */}
            <span className="text-xs text-muted-foreground/60 mt-1 block">
              {_formatDate(turn.created_at)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default TurnHistory;
