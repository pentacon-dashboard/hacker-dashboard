"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

export type AnalyzerType = "portfolio" | "crypto" | "stock";
export type PeriodDays = 30 | 90 | 180 | 365;
export type CurrencyType = "KRW" | "USD";

export interface AnalyzerConfig {
  analyzer: AnalyzerType;
  period_days: PeriodDays;
  currency: CurrencyType;
  include_fx: boolean;
}

interface AnalyzerConfigCardProps {
  config: AnalyzerConfig;
  onChange: (config: AnalyzerConfig) => void;
  disabled?: boolean;
}

const ANALYZER_OPTIONS: { value: AnalyzerType; label: string; desc: string }[] = [
  { value: "portfolio", label: "포트폴리오", desc: "다자산 포트폴리오 분석" },
  { value: "crypto", label: "암호화폐", desc: "코인 특화 분석" },
  { value: "stock", label: "주식", desc: "개별 종목·시장 분석" },
];

const PERIOD_OPTIONS: { value: PeriodDays; label: string }[] = [
  { value: 30, label: "30일" },
  { value: 90, label: "90일" },
  { value: 180, label: "180일" },
  { value: 365, label: "365일" },
];

export function AnalyzerConfigCard({ config, onChange, disabled }: AnalyzerConfigCardProps) {
  function update<K extends keyof AnalyzerConfig>(key: K, value: AnalyzerConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <Card data-testid="analyzer-config-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">4. 분석 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 분석기 선택 */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">분석기 선택</p>
          <div className="grid grid-cols-3 gap-2">
            {ANALYZER_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                disabled={disabled}
                onClick={() => update("analyzer", opt.value)}
                className={[
                  "rounded-lg border px-3 py-2 text-left transition-colors",
                  config.analyzer === opt.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border hover:border-primary/40 hover:bg-muted/40 text-foreground",
                  disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
                ].join(" ")}
                aria-pressed={config.analyzer === opt.value}
              >
                <p className="text-xs font-semibold">{opt.label}</p>
                <p className="text-xs text-muted-foreground">{opt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* 기간 + 통화 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label htmlFor="period-select" className="text-xs font-medium text-muted-foreground">
              분석 기간
            </label>
            <select
              id="period-select"
              disabled={disabled}
              value={config.period_days}
              onChange={(e) => update("period_days", Number(e.target.value) as PeriodDays)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              aria-label="분석 기간 선택"
            >
              {PERIOD_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="currency-select" className="text-xs font-medium text-muted-foreground">
              통화
            </label>
            <select
              id="currency-select"
              disabled={disabled}
              value={config.currency}
              onChange={(e) => update("currency", e.target.value as CurrencyType)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              aria-label="통화 선택"
            >
              <option value="KRW">KRW (한국원)</option>
              <option value="USD">USD (달러)</option>
            </select>
          </div>
        </div>

        {/* 환율 포함 토글 */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">환율 변동 포함</p>
            <p className="text-xs text-muted-foreground">KRW↔USD 환율 영향 분석에 포함</p>
          </div>
          <Switch
            checked={config.include_fx}
            onCheckedChange={(v) => update("include_fx", v)}
            disabled={disabled}
            aria-label="환율 변동 포함 토글"
          />
        </div>
      </CardContent>
    </Card>
  );
}
