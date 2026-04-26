"use client";

import { useCallback, useEffect, useState } from "react";
import { Switch } from "@/components/ui/switch";
import { AnalyzerResultPanel } from "@/components/analyze/analyzer-result-panel";
import { analyzeBySymbol, type AnalyzeResponse } from "@/lib/api/analyze";

const LS_KEY = "hd.includePortfolioContext";

interface SymbolAnalysisSectionProps {
  market: string;
  code: string;
}

interface AnalysisState {
  response: AnalyzeResponse;
  cacheHeader: string | null;
}

export function SymbolAnalysisSection({ market, code }: SymbolAnalysisSectionProps) {
  // 로컬스토리지에서 초기값 읽기 (기본 true — 데모 임팩트 극대화)
  const [includePortfolio, setIncludePortfolio] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    const stored = localStorage.getItem(LS_KEY);
    return stored === null ? true : stored === "true";
  });

  const [analysisState, setAnalysisState] = useState<AnalysisState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(
    async (withPortfolio: boolean) => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await analyzeBySymbol(market, code, {
          includePortfolioContext: withPortfolio,
        });
        setAnalysisState(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [market, code],
  );

  // 마운트 시 최초 분석 실행 (의도적 빈 deps — 마운트 1회만 실행)
  useEffect(() => {
    void runAnalysis(includePortfolio);
  }, []);

  function handleToggle(checked: boolean) {
    setIncludePortfolio(checked);
    localStorage.setItem(LS_KEY, String(checked));
    void runAnalysis(checked);
  }

  return (
    <div className="space-y-4">
      {/* 포트폴리오 반영 토글 */}
      <div className="flex items-center gap-3">
        <Switch
          checked={includePortfolio}
          onCheckedChange={handleToggle}
          disabled={isLoading}
          aria-label="내 포트폴리오 반영 토글"
          data-testid="portfolio-context-toggle"
        />
        <div className="space-y-0.5">
          <span className="text-sm font-medium leading-none">내 포트폴리오 반영</span>
          <p className="text-xs text-muted-foreground">
            보유 종목일 경우 평가손익·집중도를 분석에 포함합니다
          </p>
        </div>
      </div>

      {/* 분석 결과 영역 */}
      {isLoading && (
        <div
          className="flex h-32 items-center justify-center rounded-xl border bg-muted/30 text-sm text-muted-foreground"
          role="status"
          aria-live="polite"
        >
          <span className="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animate-spin"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            분석 중...
          </span>
        </div>
      )}

      {!isLoading && error && (
        <div
          className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive dark:border-destructive/50 dark:bg-destructive/20"
          role="alert"
        >
          분석 실패: {error}
        </div>
      )}

      {!isLoading && !error && analysisState && (
        <AnalyzerResultPanel
          response={analysisState.response}
          cacheHeader={analysisState.cacheHeader}
        />
      )}

      {!isLoading && !error && !analysisState && (
        <div
          className="flex h-24 items-center justify-center rounded-xl border bg-muted/30 text-sm text-muted-foreground"
          role="status"
        >
          분석 결과가 없습니다.
        </div>
      )}
    </div>
  );
}
