"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Lightbulb, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPortfolioSummary, getAiInsight } from "@/lib/api/portfolio";
import type { PortfolioSummary } from "@/lib/api/portfolio";
import type { AiInsightResponse } from "@/components/portfolio/ai-insight-card";
import { useLocale } from "@/lib/i18n/locale-provider";

interface ReferencePanelProps {
  quickQuestions?: string[];
  onQuickQuestion?: (q: string) => void;
}

export function ReferencePanel({
  quickQuestions,
  onQuickQuestion,
}: ReferencePanelProps) {
  const { t } = useLocale();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);

  const defaultQuickQuestions = [
    t("copilot.q1"),
    t("copilot.q2"),
    t("copilot.q3"),
    t("copilot.q4"),
  ];
  const resolvedQuickQuestions = quickQuestions ?? defaultQuickQuestions;

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
          <CardTitle className="text-xs font-semibold text-muted-foreground">{t("copilot.portfolioSummary")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {summaryLoading ? (
            <>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </>
          ) : summaryError ? (
            <p className="text-xs text-destructive" data-testid="summary-error">
              {t("copilot.summaryError")}
            </p>
          ) : pnlPct !== null ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{t("copilot.totalReturn")}</span>
                <span
                  className={`text-sm font-bold ${pnlPct >= 0 ? "text-green-500" : "text-destructive"}`}
                  data-testid="summary-pnl-pct"
                >
                  {pnlPct >= 0 ? "+" : ""}
                  {pnlPct.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{t("copilot.dailyChange")}</span>
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
            <p className="text-xs text-muted-foreground" data-testid="summary-empty">{t("copilot.noData")}</p>
          )}
        </CardContent>
      </Card>

      {/* AI 인사이트 요약 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Lightbulb className="h-3.5 w-3.5 text-yellow-500" aria-hidden="true" />
            {t("copilot.aiInsightSummary")}
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
              {t("copilot.insightError")}
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
            <p className="text-xs text-muted-foreground" data-testid="insight-empty">{t("copilot.noData")}</p>
          )}
        </CardContent>
      </Card>

      {/* 추천 질문 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-muted-foreground">{t("copilot.quickQuestions")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {resolvedQuickQuestions.map((q, i) => (
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
            {t("copilot.startGuide")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[
            t("copilot.guide1"),
            t("copilot.guide2"),
            t("copilot.guide3"),
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
