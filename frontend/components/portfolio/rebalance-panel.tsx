"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { AllocationCompareChart } from "@/components/portfolio/allocation-compare-chart";
import { RebalanceActionTable } from "@/components/portfolio/rebalance-action-table";
import {
  requestRebalance,
  type RebalanceResponse,
  type LLMAnalysis,
} from "@/lib/api/rebalance";

// 로컬스토리지 키
const LS_KEY = "hd.rebalanceTarget";

interface SliderTarget {
  stock_kr: number;
  stock_us: number;
  crypto: number;
  cash: number;
}

// 기본 프리셋
const PRESETS: { label: string; values: SliderTarget }[] = [
  { label: "공격형 70/30", values: { stock_kr: 10, stock_us: 30, crypto: 50, cash: 10 } },
  { label: "균형형", values: { stock_kr: 20, stock_us: 40, crypto: 30, cash: 10 } },
  { label: "안정형 30/70", values: { stock_kr: 30, stock_us: 20, crypto: 10, cash: 40 } },
];

const DEFAULT_TARGET: SliderTarget = { stock_kr: 20, stock_us: 40, crypto: 30, cash: 10 };
const TARGET_KEYS: (keyof SliderTarget)[] = ["stock_kr", "stock_us", "crypto", "cash"];

function clampSliderValue(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function balanceTargetAfterChange(
  previous: SliderTarget,
  changedKey: keyof SliderTarget,
  rawValue: number,
): SliderTarget {
  const changedValue = clampSliderValue(rawValue);
  const remaining = 100 - changedValue;
  const otherKeys = TARGET_KEYS.filter((key) => key !== changedKey);
  const previousOtherTotal = otherKeys.reduce((sum, key) => sum + previous[key], 0);
  const next: SliderTarget = { ...previous, [changedKey]: changedValue };

  if (previousOtherTotal <= 0) {
    const base = Math.floor(remaining / otherKeys.length);
    let leftover = remaining - base * otherKeys.length;

    for (const key of otherKeys) {
      next[key] = base + (leftover > 0 ? 1 : 0);
      if (leftover > 0) leftover -= 1;
    }

    return next;
  }

  const scaled = otherKeys.map((key) => {
    const exact = (previous[key] / previousOtherTotal) * remaining;
    return {
      key,
      value: Math.floor(exact),
      remainder: exact - Math.floor(exact),
    };
  });

  let leftover = remaining - scaled.reduce((sum, item) => sum + item.value, 0);
  scaled.sort((a, b) => b.remainder - a.remainder);

  for (const item of scaled) {
    next[item.key] = item.value + (leftover > 0 ? 1 : 0);
    if (leftover > 0) leftover -= 1;
  }

  return next;
}

function loadFromStorage(): SliderTarget {
  if (typeof window === "undefined") return DEFAULT_TARGET;
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return DEFAULT_TARGET;
    const parsed = JSON.parse(raw) as Partial<SliderTarget>;
    return {
      stock_kr: parsed.stock_kr ?? DEFAULT_TARGET.stock_kr,
      stock_us: parsed.stock_us ?? DEFAULT_TARGET.stock_us,
      crypto: parsed.crypto ?? DEFAULT_TARGET.crypto,
      cash: parsed.cash ?? DEFAULT_TARGET.cash,
    };
  } catch {
    return DEFAULT_TARGET;
  }
}

function saveToStorage(target: SliderTarget): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(target));
  } catch {
    // 스토리지 쓰기 실패 무시
  }
}

function confidenceColorClass(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
  if (confidence >= 0.6) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
}

function LLMAnalysisCard({ llmAnalysis }: { llmAnalysis: LLMAnalysis }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base font-semibold leading-tight">
            {llmAnalysis.headline}
          </CardTitle>
          <Badge
            className={confidenceColorClass(llmAnalysis.confidence)}
            variant="outline"
          >
            신뢰도 {Math.round(llmAnalysis.confidence * 100)}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground leading-relaxed">
          {llmAnalysis.narrative}
        </p>
        {llmAnalysis.warnings && llmAnalysis.warnings.length > 0 && (
          <div className="space-y-2">
            {llmAnalysis.warnings.map((warning, i) => (
              <Alert key={i} variant="warning">
                <AlertTitle className="text-xs font-medium">주의</AlertTitle>
                <AlertDescription className="text-xs">{warning}</AlertDescription>
              </Alert>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const SLIDER_LABELS: Record<keyof SliderTarget, string> = {
  stock_kr: "한국 주식",
  stock_us: "미국 주식",
  crypto: "암호화폐",
  cash: "현금",
};

interface RebalancePanelProps {
  clientId?: string;
}

export function RebalancePanel({ clientId = "client-001" }: RebalancePanelProps) {
  const [target, setTarget] = useState<SliderTarget>(DEFAULT_TARGET);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RebalanceResponse | null>(null);

  // 마운트 시 로컬스토리지에서 복원
  useEffect(() => {
    setTarget(loadFromStorage());
  }, []);

  const total = useMemo(
    () => target.stock_kr + target.stock_us + target.crypto + target.cash,
    [target],
  );

  const isValidTotal = Math.abs(total - 100) <= 0.1;

  const handleSliderChange = useCallback(
    (key: keyof SliderTarget, value: number) => {
      setTarget((prev) => {
        const next = balanceTargetAfterChange(prev, key, value);
        saveToStorage(next);
        return next;
      });
    },
    [],
  );

  const handlePreset = useCallback((preset: SliderTarget) => {
    setTarget(preset);
    saveToStorage(preset);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!isValidTotal) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await requestRebalance({
        client_id: clientId,
        target_allocation: {
          stock_kr: target.stock_kr / 100,
          stock_us: target.stock_us / 100,
          crypto: target.crypto / 100,
          cash: target.cash / 100,
          fx: 0,
        },
        constraints: {
          max_single_weight: 0.5,
          min_trade_krw: 100000,
          allow_fractional: true,
        },
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }, [target, isValidTotal, clientId]);

  const totalDiff = total - 100;
  const totalBadgeClass =
    Math.abs(totalDiff) <= 0.1
      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
      : totalDiff > 0
        ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
        : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";

  return (
    <div className="space-y-6">
      {/* 슬라이더 패널 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="text-base font-semibold">목표 자산 비중 설정</CardTitle>
            <Badge className={totalBadgeClass} variant="outline">
              합계 {total.toFixed(1)}%{" "}
              {!isValidTotal && (totalDiff > 0 ? `(+${totalDiff.toFixed(1)}% 초과)` : `(${totalDiff.toFixed(1)}% 부족)`)}
            </Badge>
          </div>
          {/* 프리셋 버튼 */}
          <div className="flex gap-2 flex-wrap mt-2">
            {PRESETS.map((preset) => (
              <Button
                key={preset.label}
                variant="outline"
                size="sm"
                onClick={() => handlePreset(preset.values)}
              >
                {preset.label}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {TARGET_KEYS.map((key) => (
            <div key={key} className="space-y-2">
              <div className="flex justify-between items-center">
                <label
                  htmlFor={`slider-${key}`}
                  className="text-sm font-medium"
                >
                  {SLIDER_LABELS[key]}
                </label>
                <span className="text-sm tabular-nums font-semibold w-12 text-right">
                  {target[key]}%
                </span>
              </div>
              <Slider
                id={`slider-${key}`}
                aria-label={`${SLIDER_LABELS[key]} 목표 비중`}
                min={0}
                max={100}
                step={1}
                value={target[key]}
                onValueChange={(v) => handleSliderChange(key, v)}
              />
            </div>
          ))}

          {/* 제안 받기 버튼 */}
          <div className="pt-2">
            <Button
              onClick={() => void handleSubmit()}
              disabled={!isValidTotal || isLoading}
              aria-disabled={!isValidTotal || isLoading}
              className="w-full"
            >
              {isLoading ? "분석 중..." : "제안 받기"}
            </Button>
            {!isValidTotal && (
              <p className="text-xs text-muted-foreground mt-2 text-center">
                슬라이더 합계가 100%가 되어야 제안을 받을 수 있습니다.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 에러 상태 */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>오류 발생</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 빈 상태 — 결과 없음 */}
      {!result && !error && !isLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <p className="text-lg font-medium text-muted-foreground">
                목표를 설정하고 제안을 받아보세요
              </p>
              <p className="text-sm text-muted-foreground">
                슬라이더로 목표 비중을 100%로 맞추고 "제안 받기"를 클릭하세요.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 결과 영역 */}
      {result && (
        <div className="space-y-6">
          {/* LLM 해석 카드 — degraded 배너 또는 정상 해석 */}
          {result.llm_analysis != null ? (
            <LLMAnalysisCard llmAnalysis={result.llm_analysis} />
          ) : result.status === "degraded" ? (
            <Alert>
              <AlertTitle>LLM 해석 실패</AlertTitle>
              <AlertDescription>
                LLM 해석 실패 — 계산된 액션은 유효합니다. 아래 리밸런싱 제안은 수학적으로
                정확하게 계산된 결과입니다.
              </AlertDescription>
            </Alert>
          ) : null}

          {/* 비교 차트 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">자산군 비중 비교</CardTitle>
              <p className="text-xs text-muted-foreground">
                현재(파랑) · 목표(초록) · 리밸런싱 후 예상(보라)
              </p>
            </CardHeader>
            <CardContent>
              <AllocationCompareChart
                currentAllocation={result.current_allocation}
                targetAllocation={result.target_allocation}
                expectedAllocation={result.expected_allocation}
              />
            </CardContent>
          </Card>

          {/* 요약 */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "총 거래 수", value: `${result.summary.total_trades}건` },
              { label: "총 매도액", value: result.summary.total_sell_value_krw ? `₩${Number(result.summary.total_sell_value_krw).toLocaleString("ko-KR")}` : "-" },
              { label: "총 매수액", value: result.summary.total_buy_value_krw ? `₩${Number(result.summary.total_buy_value_krw).toLocaleString("ko-KR")}` : "-" },
              { label: "예상 거래 비용", value: result.summary.rebalance_cost_estimate_krw ? `₩${Number(result.summary.rebalance_cost_estimate_krw).toLocaleString("ko-KR")}` : "-" },
            ].map(({ label, value }) => (
              <Card key={label}>
                <CardContent className="pt-4 pb-3">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-base font-semibold tabular-nums mt-1">{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* 액션 테이블 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">리밸런싱 액션</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <RebalanceActionTable actions={result.actions} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
