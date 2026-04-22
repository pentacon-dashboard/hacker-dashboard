"use client";

import type { CopilotCard } from "@/hooks/use-copilot-stream";
import { DegradedCard } from "./degraded-card";
import { TextCard } from "./text-card";

interface CardRendererProps {
  card: CopilotCard;
  stepId?: string;
}

/**
 * 카드 타입별 렌더러 디스패처.
 * degraded 플래그가 있으면 DegradedCard 를 우선 렌더한 뒤 원본 카드도 표시.
 */
export function CardRenderer({ card, stepId }: CardRendererProps) {
  const isDegraded = card.degraded === true;

  return (
    <div className="space-y-2">
      {isDegraded && (
        <DegradedCard
          reason={(card.degraded_reason as string | undefined) ?? "분석 결과 품질 저하"}
          stepId={stepId}
        />
      )}
      {card.type === "text" && <TextCard card={card as Parameters<typeof TextCard>[0]["card"]} />}
      {card.type === "chart" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [차트 카드 — sprint-06에서 TradingView 연동 예정]
        </div>
      )}
      {card.type === "scorecard" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [스코어카드 — 지표 {((card.rows as unknown[]) ?? []).length}개]
        </div>
      )}
      {card.type === "citation" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [인용 카드] {card.title as string}
        </div>
      )}
      {card.type === "comparison_table" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [비교 테이블] {((card.symbols as string[]) ?? []).join(", ")}
        </div>
      )}
      {card.type === "simulator_result" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [시뮬레이터] 충격 후 포트 가치: {card.shocked_value as number}
        </div>
      )}
    </div>
  );
}

export { DegradedCard, TextCard };
