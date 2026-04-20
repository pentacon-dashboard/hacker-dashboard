"use client";

import { useState } from "react";

interface RouterReasonPanelProps {
  routerReason?: string;
}

export function RouterReasonPanel({
  routerReason = "Analyzer 분석 결과가 여기에 표시됩니다. (analyzer-designer 구현 대기 중)",
}: RouterReasonPanelProps) {
  const [showReason, setShowReason] = useState(false);

  return (
    <div className="rounded-lg border p-4 space-y-2">
      <h2 className="text-sm font-semibold">Router 분석 근거</h2>
      <button
        data-testid="router-reason-toggle"
        aria-label="Router 결정 근거 보기"
        aria-expanded={showReason}
        onClick={() => setShowReason((v) => !v)}
        className="text-xs text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring rounded transition-colors"
      >
        {showReason ? "숨기기" : "근거 보기"}
      </button>
      {showReason && (
        <div
          data-testid="router-reason-content"
          className="mt-2 text-xs text-muted-foreground leading-relaxed"
        >
          {routerReason}
        </div>
      )}
    </div>
  );
}
