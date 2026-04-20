"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { AnalyzeResponse, CacheMetrics } from "@/lib/api/analyze";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";

interface AnalyzerResultPanelProps {
  response: AnalyzeResponse;
  cacheHeader: string | null;
  className?: string;
}

const GATE_COLORS: Record<string, string> = {
  pass: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  fail: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  warn: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  skip: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
};

const GATE_COLOR_FALLBACK = "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";

function getGateColor(status: string): string {
  const key = status.toLowerCase();
  return GATE_COLORS[key] ?? GATE_COLOR_FALLBACK;
}

function GateBadge({ name, status }: { name: string; status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        getGateColor(status),
      )}
      data-testid={`gate-badge-${name}`}
    >
      <span className="uppercase">{name}</span>
      <span className="opacity-70">{status}</span>
    </span>
  );
}

function useTypewriter(text: string, speed = 18): string {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    setDisplayed("");
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return displayed;
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color =
    clamped >= 70
      ? "bg-green-500"
      : clamped >= 40
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="space-y-1" data-testid="confidence-bar">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>신뢰도</span>
        <span className="font-semibold tabular-nums">{clamped}%</span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`신뢰도 ${clamped}%`}
      >
        <div
          className={cn("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

function SignalCard({ signal }: { signal: Record<string, unknown> }) {
  const title = (signal["label"] ?? signal["name"] ?? signal["signal"] ?? "신호") as string;
  const value = (signal["value"] ?? signal["score"] ?? signal["result"] ?? "") as string;
  const direction = (signal["direction"] ?? signal["type"] ?? "") as string;

  const directionColor =
    direction === "bullish" || direction === "buy" || direction === "positive"
      ? "text-green-600 dark:text-green-400"
      : direction === "bearish" || direction === "sell" || direction === "negative"
        ? "text-red-600 dark:text-red-400"
        : "text-muted-foreground";

  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card p-3">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      <span className="text-sm font-semibold">{String(value)}</span>
      {direction && (
        <span className={cn("text-xs font-medium", directionColor)}>{direction}</span>
      )}
    </div>
  );
}

// matched_holding 정보 타입
interface MatchedHoldingInfo {
  quantity: number | null;
  unit: string;
  pnlPct: number | null;
}

/**
 * result에서 matched_holding 정보 추출.
 * 우선순위:
 * 1. result.metrics.matched_holding (dict)
 * 2. result.matched_holding (dict)
 * 3. result.evidence[] 중 source === "portfolio.matched_holding"
 */
function extractMatchedHolding(resultMap: Record<string, unknown>): MatchedHoldingInfo | null {
  // 1순위: result.metrics.matched_holding
  const metrics = resultMap["metrics"];
  if (metrics !== null && typeof metrics === "object") {
    const metricsMap = metrics as Record<string, unknown>;
    const mh = metricsMap["matched_holding"];
    if (mh !== null && typeof mh === "object") {
      const mhMap = mh as Record<string, unknown>;
      const quantity = typeof mhMap["quantity"] === "number" ? mhMap["quantity"] : null;
      const pnlPct =
        typeof mhMap["pnl_pct"] === "number"
          ? mhMap["pnl_pct"]
          : typeof mhMap["unrealized_pnl_pct"] === "number"
            ? mhMap["unrealized_pnl_pct"]
            : null;
      const unit = (mhMap["currency"] as string | undefined) ?? "주";
      return { quantity, unit, pnlPct };
    }
  }

  // 2순위: result.matched_holding 직접 필드
  const directMh = resultMap["matched_holding"];
  if (directMh !== null && typeof directMh === "object") {
    const mhMap = directMh as Record<string, unknown>;
    const quantity = typeof mhMap["quantity"] === "number" ? mhMap["quantity"] : null;
    const pnlPct =
      typeof mhMap["pnl_pct"] === "number"
        ? mhMap["pnl_pct"]
        : typeof mhMap["unrealized_pnl_pct"] === "number"
          ? mhMap["unrealized_pnl_pct"]
          : null;
    const unit = (mhMap["currency"] as string | undefined) ?? "주";
    return { quantity, unit, pnlPct };
  }

  // 3순위: result.evidence[]에서 source === "portfolio.matched_holding"
  const evidenceArr = resultMap["evidence"];
  if (Array.isArray(evidenceArr)) {
    const portfolioEvidence = evidenceArr.find(
      (item) =>
        item !== null &&
        typeof item === "object" &&
        (item as Record<string, unknown>)["source"] === "portfolio.matched_holding",
    ) as Record<string, unknown> | undefined;
    if (portfolioEvidence) {
      // claim 파싱: "보유 5주, 평단 185 USD, 평가손익 +12.3%" 형태
      const claim = portfolioEvidence["claim"];
      if (typeof claim === "string") {
        const quantityMatch = /(\d+(?:\.\d+)?)\s*주/.exec(claim);
        const pnlMatch = /([+-]?\d+(?:\.\d+)?)\s*%/.exec(claim);
        const quantity = quantityMatch?.[1] ? parseFloat(quantityMatch[1]) : null;
        const pnlPct = pnlMatch?.[1] ? parseFloat(pnlMatch[1]) : null;
        return { quantity, unit: "주", pnlPct };
      }
      return { quantity: null, unit: "주", pnlPct: null };
    }
  }

  return null;
}

/**
 * signals에서 집중도 리스크 신호 추출
 */
function extractConcentrationRisk(signals: Record<string, unknown>[]): string | null {
  const riskSignal = signals.find(
    (s) =>
      s["kind"] === "risk" &&
      typeof s["rationale"] === "string" &&
      (s["rationale"] as string).includes("집중도"),
  );
  if (riskSignal) {
    return (riskSignal["rationale"] as string) ?? null;
  }
  return null;
}

export function AnalyzerResultPanel({
  response,
  cacheHeader,
  className,
}: AnalyzerResultPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const { meta, result, status } = response;

  // result 에서 headline, confidence, signals 추출 (자산군별 상이)
  const resultMap = (result ?? {}) as Record<string, unknown>;
  const headline = (resultMap["headline"] ?? resultMap["summary"] ?? resultMap["title"] ?? "") as string;
  const rawConfidence = resultMap["confidence"] ?? resultMap["confidence_score"] ?? null;
  const confidence = typeof rawConfidence === "number" ? rawConfidence : null;
  const signals = Array.isArray(resultMap["signals"])
    ? (resultMap["signals"] as Record<string, unknown>[])
    : [];

  // 개인화 데이터 추출
  const matchedHolding = extractMatchedHolding(resultMap);
  const concentrationRisk = extractConcentrationRisk(signals);

  const routerReason = useTypewriter(meta.router_reason ?? "");

  const cacheMetrics = meta.cache as CacheMetrics | null | undefined;

  useEffect(() => {
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [response.request_id]);

  return (
    <div
      ref={panelRef}
      className={cn(
        "animate-in fade-in slide-in-from-bottom-4 space-y-5 rounded-xl border bg-card p-5 shadow-sm duration-500",
        className,
      )}
      data-testid="analyzer-result"
      aria-label="분석 결과"
    >
      {/* 집중도 리스크 경고 배너 */}
      {concentrationRisk && (
        <Alert variant="warning" data-testid="concentration-risk-alert">
          <AlertTitle>집중도 리스크</AlertTitle>
          <AlertDescription>{concentrationRisk}</AlertDescription>
        </Alert>
      )}

      {/* 상태 + 헤드라인 */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold",
                status === "ok"
                  ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
              )}
            >
              {status.toUpperCase()}
            </span>
            {meta.analyzer_name && (
              <span className="text-xs text-muted-foreground">{meta.analyzer_name} analyzer</span>
            )}
            {/* 보유 중 배지 */}
            {matchedHolding && (
              <Badge
                variant="secondary"
                className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-transparent"
                data-testid="holding-badge"
              >
                보유 중
                {matchedHolding.quantity !== null
                  ? ` ${matchedHolding.quantity}${matchedHolding.unit}`
                  : ""}
                {matchedHolding.pnlPct !== null
                  ? `, 평가손익 ${matchedHolding.pnlPct > 0 ? "+" : ""}${matchedHolding.pnlPct.toFixed(1)}%`
                  : ""}
              </Badge>
            )}
          </div>
          {headline ? (
            <h2 className="text-base font-semibold leading-snug">{headline}</h2>
          ) : (
            <h2 className="text-base font-semibold text-muted-foreground">
              {meta.asset_class} 분석 완료
            </h2>
          )}
        </div>
        {meta.latency_ms != null && (
          <span className="shrink-0 text-xs text-muted-foreground">
            {meta.latency_ms.toLocaleString()}ms
          </span>
        )}
      </div>

      {/* 신뢰도 바 */}
      {confidence !== null && <ConfidenceBar value={confidence} />}

      {/* Router 결정 근거 */}
      <div className="space-y-1.5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Router 결정 근거
        </p>
        <p
          className="min-h-[1.5em] text-sm leading-relaxed"
          data-testid="router-reason-content"
          aria-live="polite"
        >
          {routerReason}
        </p>
      </div>

      {/* 3단 게이트 상태 */}
      {Object.keys(meta.gates).length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            품질 게이트
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(meta.gates).map(([name, status]) => (
              <GateBadge key={name} name={name} status={status} />
            ))}
          </div>
        </div>
      )}

      {/* 근거 스니펫 */}
      {meta.evidence_snippets && meta.evidence_snippets.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            근거 인용
          </p>
          <ul className="space-y-1.5" role="list">
            {meta.evidence_snippets.map((snippet, i) => (
              <li
                key={i}
                className="rounded-md border-l-2 border-primary/40 bg-muted/30 px-3 py-1.5 text-xs leading-relaxed"
              >
                {snippet}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 시그널 카드 3열 */}
      {signals.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            시그널
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {signals.map((signal, i) => (
              <SignalCard key={i} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* 캐시 메트릭 footer */}
      <div className="flex flex-col gap-1 border-t pt-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span>Request ID: {response.request_id}</span>
        {cacheMetrics ? (
          <span>
            이 응답은 캐시{" "}
            <span className="font-medium tabular-nums text-foreground">
              {cacheMetrics.read_tokens.toLocaleString()}
            </span>
            /
            <span className="font-medium tabular-nums text-foreground">
              {cacheMetrics.creation_tokens.toLocaleString()}
            </span>{" "}
            토큰을 사용했습니다
          </span>
        ) : cacheHeader ? (
          <span>X-Cache: {cacheHeader}</span>
        ) : null}
      </div>
    </div>
  );
}
