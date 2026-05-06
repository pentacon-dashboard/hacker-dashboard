"use client";

import Link from "next/link";
import { LineChart } from "lucide-react";
import { SectionCard } from "@/components/dashboard/section-card";
import { AssetBadge } from "@/components/common/asset-badge";
import { SymbolLookupForm } from "@/components/symbol/symbol-lookup-form";
import { useLocale } from "@/lib/i18n/locale-provider";

type Popular = {
  market: string;
  code: string;
  name: string;
  assetClass: "crypto" | "stock";
};

const POPULAR_SYMBOLS: Popular[] = [
  { market: "upbit", code: "KRW-BTC", name: "비트코인", assetClass: "crypto" },
  { market: "upbit", code: "KRW-ETH", name: "이더리움", assetClass: "crypto" },
  { market: "upbit", code: "KRW-XRP", name: "리플", assetClass: "crypto" },
  { market: "upbit", code: "KRW-SOL", name: "솔라나", assetClass: "crypto" },
  { market: "yahoo", code: "NVDA", name: "NVIDIA", assetClass: "stock" },
  { market: "yahoo", code: "AAPL", name: "Apple", assetClass: "stock" },
  { market: "yahoo", code: "TSLA", name: "Tesla", assetClass: "stock" },
  { market: "yahoo", code: "MSFT", name: "Microsoft", assetClass: "stock" },
  { market: "naver_kr", code: "005930", name: "삼성전자", assetClass: "stock" },
  { market: "naver_kr", code: "000660", name: "SK하이닉스", assetClass: "stock" },
  { market: "naver_kr", code: "035420", name: "NAVER", assetClass: "stock" },
  { market: "naver_kr", code: "035720", name: "카카오", assetClass: "stock" },
];

export default function SymbolLandingPage() {
  const { t } = useLocale();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <LineChart className="h-7 w-7 text-primary" aria-hidden="true" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("sidebar.symbol")}</h1>
          <p className="text-sm text-muted-foreground">
            종목을 검색하거나 아래 인기 종목을 선택하세요. 코인은 KRW-BTC, 한국주식은 6자리 코드, 그 외는 티커 입력.
          </p>
        </div>
      </div>

      {/* 검색 */}
      <SectionCard title="검색">
        <SymbolLookupForm />
      </SectionCard>

      {/* 인기 종목 */}
      <SectionCard title="인기 종목">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {POPULAR_SYMBOLS.map((sym) => (
            <Link
              key={`${sym.market}/${sym.code}`}
              href={`/symbol/${sym.market}/${encodeURIComponent(sym.code)}`}
              className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 transition hover:border-primary/60 hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">{sym.name}</span>
                <span className="text-xs text-muted-foreground">{sym.code}</span>
              </div>
              <AssetBadge assetClass={sym.assetClass} />
            </Link>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
