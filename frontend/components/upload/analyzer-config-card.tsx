"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { useLocale } from "@/lib/i18n/locale-provider";

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

const PERIOD_OPTIONS: { value: PeriodDays }[] = [
  { value: 30 },
  { value: 90 },
  { value: 180 },
  { value: 365 },
];

export function AnalyzerConfigCard({ config, onChange, disabled }: AnalyzerConfigCardProps) {
  const { t } = useLocale();

  const ANALYZER_OPTIONS: { value: AnalyzerType; label: string; desc: string }[] = [
    { value: "portfolio", label: t("upload.config.analyzer.portfolio"), desc: t("upload.config.analyzer.portfolio.desc") },
    { value: "crypto", label: t("upload.config.analyzer.crypto"), desc: t("upload.config.analyzer.crypto.desc") },
    { value: "stock", label: t("upload.config.analyzer.stock"), desc: t("upload.config.analyzer.stock.desc") },
  ];

  const PERIOD_LABELS: Record<PeriodDays, string> = {
    30: t("upload.config.period.30"),
    90: t("upload.config.period.90"),
    180: t("upload.config.period.180"),
    365: t("upload.config.period.365"),
  };

  function update<K extends keyof AnalyzerConfig>(key: K, value: AnalyzerConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <Card data-testid="analyzer-config-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{t("upload.section.config")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 분석기 선택 */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">{t("upload.config.analyzer")}</p>
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
              {t("upload.config.period")}
            </label>
            <select
              id="period-select"
              disabled={disabled}
              value={config.period_days}
              onChange={(e) => update("period_days", Number(e.target.value) as PeriodDays)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              aria-label={t("upload.config.period")}
            >
              {PERIOD_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {PERIOD_LABELS[opt.value]}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="currency-select" className="text-xs font-medium text-muted-foreground">
              {t("upload.config.currency")}
            </label>
            <select
              id="currency-select"
              disabled={disabled}
              value={config.currency}
              onChange={(e) => update("currency", e.target.value as CurrencyType)}
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              aria-label={t("upload.config.currency")}
            >
              <option value="KRW">KRW</option>
              <option value="USD">USD</option>
            </select>
          </div>
        </div>

        {/* 환율 포함 토글 */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div>
            <p className="text-xs font-medium">{t("upload.config.includeFx")}</p>
            <p className="text-xs text-muted-foreground">{t("upload.config.includeFx.desc")}</p>
          </div>
          <Switch
            checked={config.include_fx}
            onCheckedChange={(v) => update("include_fx", v)}
            disabled={disabled}
            aria-label={t("upload.config.includeFx")}
          />
        </div>
      </CardContent>
    </Card>
  );
}
