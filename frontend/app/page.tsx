"use client";

import { useRef, useState } from "react";
import { WatchlistSummary } from "@/components/dashboard/watchlist-summary";
import { CsvDropzone } from "@/components/analyze/csv-dropzone";
import { AnalyzerResultPanel } from "@/components/analyze/analyzer-result-panel";
import { useToast } from "@/hooks/use-toast";
import { analyzeBySymbol, analyzeCsv, type AnalyzeResponse } from "@/lib/api/analyze";

type DemoType = "stocks" | "crypto" | "mixed";

const DEMO_LABELS: Record<DemoType, string> = {
  stocks: "주식 샘플",
  crypto: "코인 샘플",
  mixed: "혼합 샘플",
};

interface LiveSymbol {
  id: string;
  label: string;
  market: string;
  code: string;
}

const LIVE_SYMBOLS: LiveSymbol[] = [
  { id: "btc", label: "비트코인 (KRW-BTC, 90일)", market: "upbit", code: "KRW-BTC" },
  { id: "eth", label: "이더리움 (KRW-ETH, 90일)", market: "upbit", code: "KRW-ETH" },
  { id: "aapl", label: "Apple (AAPL, 90일)", market: "yahoo", code: "AAPL" },
  { id: "tsla", label: "Tesla (TSLA, 90일)", market: "yahoo", code: "TSLA" },
  { id: "nvda", label: "NVIDIA (NVDA, 90일)", market: "yahoo", code: "NVDA" },
  { id: "samsung", label: "삼성전자 (005930.KS, 90일)", market: "yahoo", code: "005930.KS" },
];

interface AnalysisResult {
  response: AnalyzeResponse;
  cacheHeader: string | null;
}

export default function HomePage() {
  const resultRef = useRef<HTMLDivElement>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [demoLoading, setDemoLoading] = useState<DemoType | null>(null);
  const [liveLoading, setLiveLoading] = useState<string | null>(null);
  const { toast } = useToast();

  function handleResult(data: AnalysisResult) {
    setAnalysisResult(data);
    toast({ title: "분석 완료", variant: "success" });
    setTimeout(() => {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  function handleError(message: string) {
    toast({ title: "분석 실패", description: message, variant: "error" });
  }

  async function handleDemo(type: DemoType) {
    if (demoLoading) return;
    setDemoLoading(type);
    try {
      const res = await fetch(`/demo/${type}.csv`);
      if (!res.ok) throw new Error(`샘플 파일 로드 실패: ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], `${type}.csv`, { type: "text/csv" });
      const result = await analyzeCsv(file);
      handleResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "데모 분석 중 오류가 발생했습니다.";
      handleError(message);
    } finally {
      setDemoLoading(null);
    }
  }

  async function handleLive(sym: LiveSymbol) {
    if (liveLoading) return;
    setLiveLoading(sym.id);
    try {
      const result = await analyzeBySymbol(sym.market, sym.code);
      handleResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "실시간 분석 중 오류가 발생했습니다.";
      handleError(message);
    } finally {
      setLiveLoading(null);
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero 섹션 */}
      <section aria-labelledby="hero-heading">
        <div className="space-y-1">
          <h1 id="hero-heading" className="text-2xl font-bold tracking-tight">
            자동 분석 대시보드
          </h1>
          <p className="text-sm text-muted-foreground">
            CSV 데이터를 업로드하면 자산군을 자동 감지하고 분석 결과를 생성합니다.
          </p>
        </div>

        <div className="mt-4 rounded-xl border bg-card p-5 shadow-sm">
          <CsvDropzone onResult={handleResult} onError={handleError} />
        </div>
      </section>

      {/* 실시간 시장 데이터로 분석 */}
      <section aria-labelledby="live-heading">
        <h2
          id="live-heading"
          className="mb-3 text-sm font-semibold text-muted-foreground"
        >
          실제 시장 데이터로 분석 (최근 90일 OHLC 자동 조회)
        </h2>
        <div className="flex flex-wrap gap-2">
          {LIVE_SYMBOLS.map((sym) => (
            <button
              key={sym.id}
              type="button"
              onClick={() => handleLive(sym)}
              disabled={liveLoading !== null || demoLoading !== null}
              aria-label={`${sym.label} 실시간 분석`}
              className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {liveLoading === sym.id ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
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
              ) : null}
              {sym.label}
            </button>
          ))}
        </div>
      </section>

      {/* 심사용 데모 CTA */}
      <section aria-labelledby="demo-heading">
        <h2
          id="demo-heading"
          className="mb-3 text-sm font-semibold text-muted-foreground"
        >
          샘플 CSV (빈약한 데이터, 게이트 동작 확인용)
        </h2>
        <div className="flex flex-wrap gap-3">
          {(["stocks", "crypto", "mixed"] as DemoType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => handleDemo(type)}
              disabled={demoLoading !== null}
              aria-label={`${DEMO_LABELS[type]} 자동 분석 데모`}
              className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {demoLoading === type ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
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
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              )}
              {DEMO_LABELS[type]}
            </button>
          ))}
        </div>
      </section>

      {/* 분석 결과 패널 */}
      {analysisResult && (
        <section ref={resultRef} aria-labelledby="result-heading">
          <h2
            id="result-heading"
            className="mb-3 text-sm font-semibold text-muted-foreground"
          >
            분석 결과
          </h2>
          <AnalyzerResultPanel
            response={analysisResult.response}
            cacheHeader={analysisResult.cacheHeader}
          />
        </section>
      )}

      {/* 워치리스트 요약 */}
      <section aria-labelledby="watchlist-summary-heading">
        <h2
          id="watchlist-summary-heading"
          className="mb-3 text-sm font-semibold text-muted-foreground"
        >
          워치리스트 요약 (상위 5개)
        </h2>
        <WatchlistSummary />
      </section>
    </div>
  );
}
