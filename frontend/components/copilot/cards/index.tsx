"use client";

import type { CopilotCard } from "@/hooks/use-copilot-stream";
import { DegradedCard } from "./degraded-card";
import { TextCard } from "./text-card";

interface CardRendererProps {
  card: CopilotCard;
  stepId?: string;
  /**
   * true 일 때 degraded 배너(DegradedCard)를 렌더하지 않는다.
   * Final card 처럼 별도 컨텍스트에서 degraded 표시가 중복되지 않게 할 때 사용.
   */
  suppressDegradedBanner?: boolean;
}

/**
 * 카드 타입별 렌더러 디스패처.
 * degraded 플래그가 있으면 DegradedCard 를 우선 렌더한 뒤 원본 카드도 표시.
 * 각 카드 래퍼에 data-testid="copilot-card-{type}" 를 부여해 Playwright 에서 조회 가능.
 */
export function CardRenderer({ card, stepId, suppressDegradedBanner = false }: CardRendererProps) {
  const isDegraded = card.degraded === true;

  return (
    <div className="space-y-2" data-testid={`copilot-card-${card.type}`}>
      {isDegraded && !suppressDegradedBanner && (
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
      {card.type === "news_rag_list" && (
        <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          [뉴스 RAG] {((card.items as unknown[]) ?? []).length}개 뉴스
        </div>
      )}
    </div>
  );
}

export { DegradedCard, TextCard };
