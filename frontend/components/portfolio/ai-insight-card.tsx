"use client";

import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n/locale-provider";

export interface AiInsightResponse {
  summary: string;
  bullets: string[];
  generated_at: string;
  stub_mode: boolean;
  gates: {
    schema?: string;
    domain?: string;
    critique?: string;
    [key: string]: string | undefined;
  };
}

interface AiInsightCardProps {
  insight: AiInsightResponse | null;
  isLoading?: boolean;
}

function GateBadge({ name, status }: { name: string; status: string | undefined }) {
  const pass = status === "pass" || status === "ok";
  const pending = status == null;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
        pending
          ? "bg-muted text-muted-foreground"
          : pass
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
            : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
      }`}
      aria-label={`${name} 게이트 ${pass ? "통과" : pending ? "대기" : "실패"}`}
    >
      {pending ? (
        <Loader2 className="h-2.5 w-2.5 animate-spin" aria-hidden="true" />
      ) : pass ? (
        <CheckCircle2 className="h-2.5 w-2.5" aria-hidden="true" />
      ) : (
        <XCircle className="h-2.5 w-2.5" aria-hidden="true" />
      )}
      {name}
    </span>
  );
}

export function AiInsightCard({ insight, isLoading = false }: AiInsightCardProps) {
  const { t, locale } = useLocale();

  if (isLoading) {
    return (
      <div
        className="flex h-32 items-center justify-center gap-2 text-sm text-muted-foreground"
        data-testid="ai-insight-loading"
      >
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("portfolio.aiInsight.generating")}
      </div>
    );
  }

  if (!insight) {
    return (
      <div
        className="flex h-32 items-center justify-center text-sm text-muted-foreground"
        data-testid="ai-insight-empty"
      >
        {t("portfolio.aiInsight.empty")}
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="ai-insight-card">
      {/* 헤더: stub 배지 + 생성 시각 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {insight.stub_mode && (
            <Badge variant="outline" className="text-[10px] text-muted-foreground">
              STUB
            </Badge>
          )}
          <span className="text-[10px] text-muted-foreground">
            {new Date(insight.generated_at).toLocaleString(locale === "en" ? "en-US" : "ko-KR", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        {/* 3 gates 배지 */}
        <div className="flex items-center gap-1" data-testid="ai-insight-gates">
          <GateBadge name="Schema" status={insight.gates["schema"]} />
          <GateBadge name="Domain" status={insight.gates["domain"]} />
          <GateBadge name="Critique" status={insight.gates["critique"]} />
        </div>
      </div>

      {/* Summary */}
      <p
        className="text-xs leading-relaxed text-foreground"
        data-testid="ai-insight-summary"
      >
        {insight.summary}
      </p>

      {/* Bullets */}
      {insight.bullets.length > 0 && (
        <ul className="space-y-1" data-testid="ai-insight-bullets">
          {insight.bullets.map((b, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <span
                className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60"
                aria-hidden="true"
              />
              {b}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
