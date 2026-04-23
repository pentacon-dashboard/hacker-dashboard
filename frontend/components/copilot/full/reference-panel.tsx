"use client";

import { TrendingUp, TrendingDown, Target, Shield, Lightbulb, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PortfolioSummary {
  total_value_krw?: string;
  total_pnl_pct?: string;
  daily_change_pct?: string;
  sharpe_ratio?: number;
  win_rate_pct?: number;
  beta?: number;
  alpha?: number;
}

interface RecentActivity {
  id: string;
  type: "buy" | "sell" | "analysis";
  description: string;
  time: string;
}

interface ReferencePanelProps {
  portfolioSummary?: PortfolioSummary;
  recentActivities?: RecentActivity[];
  quickQuestions?: string[];
  onQuickQuestion?: (q: string) => void;
}

const DEFAULT_QUICK_QUESTIONS = [
  "현재 포트폴리오 리스크 수준은?",
  "다음 달 수익률 예측은?",
  "리밸런싱 추천 종목은?",
  "환율 리스크 영향은?",
];

const DEFAULT_ACTIVITIES: RecentActivity[] = [
  { id: "a1", type: "analysis", description: "포트폴리오 리밸런싱 분석 완료", time: "1시간 전" },
  { id: "a2", type: "buy", description: "AAPL 12주 매수", time: "3일 전" },
  { id: "a3", type: "sell", description: "MSFT 5주 매도", time: "5일 전" },
];

export function ReferencePanel({
  portfolioSummary,
  recentActivities = DEFAULT_ACTIVITIES,
  quickQuestions = DEFAULT_QUICK_QUESTIONS,
  onQuickQuestion,
}: ReferencePanelProps) {
  const summary = portfolioSummary;
  const pnlPct = parseFloat(summary?.total_pnl_pct ?? "4.77");
  const dailyPct = parseFloat(summary?.daily_change_pct ?? "2.04");
  const winRate = summary?.win_rate_pct ?? 68;
  const beta = summary?.beta ?? -8.35;
  const alpha = summary?.alpha ?? 12.45;
  const sharpe = summary?.sharpe_ratio ?? 0.62;

  const metrics = [
    {
      label: "승률",
      value: `${winRate}`,
      unit: "",
      icon: Target,
      color: winRate >= 60 ? "text-green-500" : "text-destructive",
    },
    {
      label: "베타",
      value: beta.toFixed(2),
      unit: "%",
      icon: Activity,
      color: Math.abs(beta) <= 10 ? "text-foreground" : "text-yellow-500",
    },
    {
      label: "알파",
      value: `+${alpha.toFixed(2)}`,
      unit: "%",
      icon: TrendingUp,
      color: alpha > 0 ? "text-green-500" : "text-destructive",
    },
    {
      label: "샤프",
      value: sharpe.toFixed(2),
      unit: "",
      icon: Shield,
      color: sharpe >= 0.5 ? "text-green-500" : "text-yellow-500",
    },
  ];

  return (
    <div className="flex flex-col gap-3 h-full" data-testid="reference-panel">
      {/* 포트폴리오 요약 카드 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-muted-foreground">포트폴리오 요약</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">총 수익률</span>
            <span className={`text-sm font-bold ${pnlPct >= 0 ? "text-green-500" : "text-destructive"}`}>
              {pnlPct >= 0 ? "+" : ""}
              {pnlPct.toFixed(2)}%
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">일간 변동</span>
            <div className="flex items-center gap-1">
              {dailyPct >= 0 ? (
                <TrendingUp className="h-3 w-3 text-green-500" aria-hidden="true" />
              ) : (
                <TrendingDown className="h-3 w-3 text-destructive" aria-hidden="true" />
              )}
              <span className={`text-xs font-semibold ${dailyPct >= 0 ? "text-green-500" : "text-destructive"}`}>
                {dailyPct >= 0 ? "+" : ""}
                {dailyPct.toFixed(2)}%
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI 인사이트 — 4 게이지 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Lightbulb className="h-3.5 w-3.5 text-yellow-500" aria-hidden="true" />
            AI 인사이트 요약
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            {metrics.map((m) => (
              <div
                key={m.label}
                className="rounded-lg border border-border bg-muted/20 px-2 py-2 text-center"
              >
                <m.icon className={`mx-auto mb-1 h-3.5 w-3.5 ${m.color}`} aria-hidden="true" />
                <p className={`text-base font-bold tabular-nums ${m.color}`}>
                  {m.value}
                  <span className="text-xs">{m.unit}</span>
                </p>
                <p className="text-[10px] text-muted-foreground">{m.label}</p>
              </div>
            ))}
          </div>
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

      {/* 최근 활동 */}
      <Card className="flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-muted-foreground">최근 활동</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {recentActivities.map((activity) => (
            <div key={activity.id} className="flex items-start gap-2">
              <div
                className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  activity.type === "buy"
                    ? "bg-green-500"
                    : activity.type === "sell"
                      ? "bg-destructive"
                      : "bg-primary"
                }`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-foreground">{activity.description}</p>
                <p className="text-[10px] text-muted-foreground">{activity.time}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
