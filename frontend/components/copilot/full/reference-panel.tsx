"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Lightbulb, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getPortfolioSummary, getAiInsight } from "@/lib/api/portfolio";
import type { PortfolioSummary } from "@/lib/api/portfolio";
import type { AiInsightResponse } from "@/components/portfolio/ai-insight-card";

interface ReferencePanelProps {
  quickQuestions?: string[];
  onQuickQuestion?: (q: string) => void;
}

const DEFAULT_QUICK_QUESTIONS = [
  "현재 포트폴리오 리스크 수준은?",
  "다음 달 수익률 예측은?",
  "리밸런싱 추천 종목은?",
  "환율 리스크 영향은?",
];

export function ReferencePanel({
  quickQuestions = DEFAULT_QUICK_QUESTIONS,
  onQuickQuestion,
}: ReferencePanelProps) {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);

  const [insight, setInsight] = useState<AiInsightResponse | null>(null);
  const [insightLoading, setInsightLoading] = useState(true);
  const [insightError, setInsightError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSummaryLoading(true);
    setSummaryError(false);

    getPortfolioSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setSummaryError(true);
      })
      .finally(() => {
        if (!cancelled) setSummaryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setInsightLoading(true);
    setInsightError(false);

    getAiInsight()
      .then((data) => {
        if (!cancelled) setInsight(data);
      })
      .catch(() => {
        if (!cancelled) setInsightError(true);
      })
      .finally(() => {
        if (!cancelled) setInsightLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const pnlPct = summary ? parseFloat(String(summary.total_pnl_pct)) : null;
  const dailyPct = summary ? parseFloat(String(summary.daily_change_pct)) : null;

  return (
    <div className="flex flex-col gap-3 h-full" data-testid="reference-panel">
      {/* 포트폴리오 요약 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-muted-foreground">포트폴리오 요약</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {summaryLoading ? (
            <>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </>
          ) : summaryError ? (
            <p className="text-xs text-destructive" data-testid="summary-error">
              데이터를 불러올 수 없습니다
            </p>
          ) : pnlPct !== null ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">총 수익률</span>
                <span
                  className={`text-sm font-bold ${pnlPct >= 0 ? "text-green-500" : "text-destructive"}`}
                  data-testid="summary-pnl-pct"
                >
                  {pnlPct >= 0 ? "+" : ""}
                  {pnlPct.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">일간 변동</span>
                <div className="flex items-center gap-1">
                  {(dailyPct ?? 0) >= 0 ? (
                    <TrendingUp className="h-3 w-3 text-green-500" aria-hidden="true" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-destructive" aria-hidden="true" />
                  )}
                  <span
                    className={`text-xs font-semibold ${(dailyPct ?? 0) >= 0 ? "text-green-500" : "text-destructive"}`}
                    data-testid="summary-daily-pct"
                  >
                    {(dailyPct ?? 0) >= 0 ? "+" : ""}
                    {(dailyPct ?? 0).toFixed(2)}%
                  </span>
                </div>
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground" data-testid="summary-empty">데이터 없음</p>
          )}
        </CardContent>
      </Card>

      {/* AI 인사이트 요약 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Lightbulb className="h-3.5 w-3.5 text-yellow-500" aria-hidden="true" />
            AI 인사이트 요약
            {insight?.stub_mode && (
              <Badge variant="outline" className="ml-auto text-[10px] text-muted-foreground">
                STUB
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {insightLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-5/6" />
              <Skeleton className="h-3 w-4/5" />
            </div>
          ) : insightError ? (
            <p className="text-xs text-destructive" data-testid="insight-error">
              AI 인사이트를 불러올 수 없습니다
            </p>
          ) : insight ? (
            <div className="space-y-2" data-testid="ai-insight-reference">
              <p className="text-xs leading-relaxed text-foreground">{insight.summary}</p>
              {insight.bullets.length > 0 && (
                <ul className="space-y-1">
                  {insight.bullets.slice(0, 3).map((b, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <span
                        className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary/60"
                        aria-hidden="true"
                      />
                      {b}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground" data-testid="insight-empty">데이터 없음</p>
          )}
        </CardContent>
      </Card>

      {/* 추천 질문 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-muted-foreground">추천 질문</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {quickQuestions.map((q, i) => (
            <button
              key={i}
              onClick={() => onQuickQuestion?.(q)}
              className="w-full rounded-lg border border-border bg-muted/20 px-2.5 py-1.5 text-left text-xs text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-primary transition-colors"
              data-testid={`quick-question-${i}`}
            >
              {q}
            </button>
          ))}
        </CardContent>
      </Card>

      {/* 시작 가이드 — 최근 활동 대체 (BE 엔드포인트 없음) */}
      <Card className="flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            새 대화 시작 가이드
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[
            "포트폴리오 파일을 업로드하면 AI 가 자동 분석을 시작합니다.",
            "위 추천 질문을 클릭하면 바로 대화를 시작할 수 있습니다.",
            "세션을 저장해 이전 분석을 이어서 확인하세요.",
          ].map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/40" aria-hidden="true" />
              <p className="text-xs text-muted-foreground">{tip}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
