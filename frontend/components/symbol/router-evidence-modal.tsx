"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useLocale } from "@/lib/i18n/locale-provider";

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
};

const ANALYZER_MAP: Record<string, string> = {
  crypto: "crypto_analyzer",
  stock: "stock_analyzer",
  macro: "macro_analyzer",
};

interface RouterEvidenceModalProps {
  market: string;
  code: string;
}

interface GateBadgeProps {
  label: string;
}

function GateBadge({ label }: GateBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
      <svg
        className="h-3 w-3"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M2 6l3 3 5-5"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {label}
    </span>
  );
}

/** Router 동작 방식을 설명하는 정적 모달 */
export function RouterEvidenceModal({ market, code }: RouterEvidenceModalProps) {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);

  const assetClass = ASSET_CLASS_MAP[market] ?? "macro";
  const analyzerName = ANALYZER_MAP[assetClass] ?? "macro_analyzer";
  const selectedAnalyzerDesc =
    `${market} + ${assetClass} → \`${analyzerName}\``;

  return (
    <>
      <div className="rounded-lg border p-4 space-y-2">
        <h2 className="text-sm font-semibold">{t("symbol.routerEvidence")}</h2>
        <button
          data-testid="router-reason-toggle"
          aria-label={t("symbol.viewEvidence")}
          aria-haspopup="dialog"
          onClick={() => setOpen(true)}
          className="text-xs text-primary hover:text-primary/80 focus:outline-none focus:ring-2 focus:ring-ring rounded transition-colors underline-offset-2 hover:underline"
        >
          {t("symbol.viewEvidence")}
        </button>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          data-testid="router-evidence-dialog"
          className="max-w-md"
          aria-describedby="router-evidence-body"
        >
          <DialogHeader>
            <DialogTitle>{t("symbol.routerEvidence.title")}</DialogTitle>
          </DialogHeader>

          <div id="router-evidence-body" className="space-y-4 text-sm">
            {/* 설명 */}
            <p className="text-muted-foreground leading-relaxed">
              {t("symbol.routerEvidence.body")}
            </p>

            {/* Router 플로우차트 SVG */}
            <div aria-hidden="true" className="rounded-lg border bg-muted/30 p-3">
              <svg
                viewBox="0 0 320 80"
                className="w-full h-auto text-foreground"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Input */}
                <rect x="4" y="24" width="56" height="28" rx="6" fill="currentColor" fillOpacity="0.1" stroke="currentColor" strokeOpacity="0.3" strokeWidth="1"/>
                <text x="32" y="41" textAnchor="middle" fontSize="8" fill="currentColor" fontFamily="monospace">Input</text>

                {/* Arrow */}
                <line x1="60" y1="38" x2="76" y2="38" stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.5" markerEnd="url(#arr)"/>

                {/* Router */}
                <rect x="76" y="20" width="64" height="36" rx="6" fill="hsl(var(--primary))" fillOpacity="0.15" stroke="hsl(var(--primary))" strokeOpacity="0.6" strokeWidth="1.5"/>
                <text x="108" y="37" textAnchor="middle" fontSize="8" fill="hsl(var(--primary))" fontFamily="monospace" fontWeight="bold">Router</text>
                <text x="108" y="48" textAnchor="middle" fontSize="6.5" fill="hsl(var(--primary))" fontFamily="monospace">(Meta Agent)</text>

                {/* Arrow */}
                <line x1="140" y1="38" x2="156" y2="38" stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.5" markerEnd="url(#arr)"/>

                {/* Analyzer */}
                <rect x="156" y="20" width="72" height="36" rx="6" fill="hsl(var(--primary))" fillOpacity="0.08" stroke="currentColor" strokeOpacity="0.3" strokeWidth="1"/>
                <text x="192" y="37" textAnchor="middle" fontSize="8" fill="currentColor" fontFamily="monospace">Analyzer</text>
                <text x="192" y="48" textAnchor="middle" fontSize="6.5" fill="currentColor" fontFamily="monospace">(Sub Agent)</text>

                {/* Arrow */}
                <line x1="228" y1="38" x2="244" y2="38" stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.5" markerEnd="url(#arr)"/>

                {/* Gate */}
                <rect x="244" y="20" width="68" height="36" rx="6" fill="hsl(142 76% 36% / 0.12)" stroke="hsl(142 76% 36% / 0.5)" strokeWidth="1"/>
                <text x="278" y="37" textAnchor="middle" fontSize="8" fill="hsl(142 76% 36%)" fontFamily="monospace" fontWeight="bold">3-Gate</text>
                <text x="278" y="48" textAnchor="middle" fontSize="6" fill="hsl(142 76% 36%)" fontFamily="monospace">Quality Check</text>

                <defs>
                  <marker id="arr" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
                    <path d="M0,0 L5,2.5 L0,5 Z" fill="currentColor" fillOpacity="0.5"/>
                  </marker>
                </defs>
              </svg>
            </div>

            {/* 선택된 Analyzer */}
            <div className="rounded-lg border bg-muted/20 px-3 py-2 space-y-1">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {t("symbol.routerEvidence.selectedAnalyzer")}
              </p>
              <p className="font-mono text-xs">
                {selectedAnalyzerDesc}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("symbol.routerEvidence.symbolCode")}: {code}
              </p>
            </div>

            {/* 3단 게이트 배지 */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {t("symbol.routerEvidence.gates")}
              </p>
              <div className="flex flex-wrap gap-2" data-testid="router-gate-badges">
                <GateBadge label={t("symbol.routerEvidence.gateSchema")} />
                <GateBadge label={t("symbol.routerEvidence.gateDomain")} />
                <GateBadge label={t("symbol.routerEvidence.gateCritique")} />
              </div>
            </div>

            {/* 닫기 버튼 */}
            <div className="flex justify-end pt-2">
              <button
                data-testid="router-evidence-close"
                onClick={() => setOpen(false)}
                className="rounded-md border px-4 py-1.5 text-sm font-medium hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
              >
                {t("common.close")}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
