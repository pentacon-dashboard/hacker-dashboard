import { Suspense } from "react";
import { notFound } from "next/navigation";
import { getOhlc, getQuote, type OhlcBar } from "@/lib/api/symbols";
import { ApiError } from "@/lib/api/client";
import { AssetBadge } from "@/components/common/asset-badge";
import { ChartWrapper } from "@/components/symbol/chart-wrapper";
import { RealtimePrice } from "@/components/symbol/realtime-price";
import { RouterReasonPanel } from "@/components/symbol/router-reason-panel";
import { SymbolAnalysisSection } from "@/components/symbol/symbol-analysis-section";

export const dynamic = "force-dynamic";

interface PageParams {
  params: Promise<{ market: string; code: string }>;
}

const ASSET_CLASS_MAP: Record<string, string> = {
  upbit: "crypto",
  binance: "crypto",
  yahoo: "stock",
  naver_kr: "stock",
};

function formatVolume(volume: number | null | undefined, currency: string) {
  if (volume == null) return "-";
  if (currency === "KRW") {
    if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
    if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  }
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(2)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(2)}K`;
  return volume.toFixed(2);
}

export default async function SymbolDetailPage({ params }: PageParams) {
  const { market, code } = await params;
  const decodedMarket = decodeURIComponent(market);
  const decodedCode = decodeURIComponent(code);

  let quote: Awaited<ReturnType<typeof getQuote>> | null;
  let ohlcData: OhlcBar[];

  try {
    [quote, ohlcData] = await Promise.all([
      getQuote(decodedMarket, decodedCode),
      getOhlc(decodedMarket, decodedCode, "1d", 180),
    ]);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    // BE 에러 → 빈 상태로 렌더 (클라이언트에서 재시도)
    ohlcData = [];
    quote = null;
  }

  const assetClass = ASSET_CLASS_MAP[decodedMarket] ?? "macro";
  const currency = quote?.currency ?? (decodedMarket === "upbit" ? "KRW" : "USD");

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{decodedCode}</h1>
            <AssetBadge assetClass={assetClass} />
            <span className="text-sm text-muted-foreground">{decodedMarket}</span>
          </div>
          {quote ? (
            <Suspense
              fallback={
                <div className="h-10 w-48 animate-pulse rounded bg-muted" />
              }
            >
              <RealtimePrice
                market={decodedMarket}
                code={decodedCode}
                initialQuote={quote}
              />
            </Suspense>
          ) : (
            <p className="text-sm text-muted-foreground">시세 데이터를 불러올 수 없습니다.</p>
          )}
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {/* 캔들차트 */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground">
            일봉 차트 (MA20 / MA60)
          </h2>
          {ohlcData.length > 0 ? (
            <ChartWrapper
              data={ohlcData}
              market={decodedMarket}
              code={decodedCode}
            />
          ) : (
            <div
              className="flex h-[400px] items-center justify-center rounded-lg border bg-muted/30 text-sm text-muted-foreground"
              role="status"
            >
              차트 데이터를 불러올 수 없습니다.
            </div>
          )}
        </div>

        {/* 사이드 메타 */}
        <aside className="space-y-4">
          {/* 기본 메타 */}
          <div className="rounded-lg border p-4 space-y-3">
            <h2 className="text-sm font-semibold">기본 정보</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">거래소</dt>
                <dd className="font-medium">{decodedMarket}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">통화</dt>
                <dd className="font-medium">{currency}</dd>
              </div>
              {quote?.volume != null && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">거래량</dt>
                  <dd className="font-medium tabular-nums">
                    {formatVolume(quote.volume, currency)}
                  </dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-muted-foreground">자산군</dt>
                <dd>
                  <AssetBadge assetClass={assetClass} />
                </dd>
              </div>
            </dl>
          </div>

          {/* Router 결정 근거 */}
          <RouterReasonPanel />
        </aside>
      </div>

      {/* 분석 결과 + 포트폴리오 반영 토글 */}
      <section aria-labelledby="analysis-section-heading">
        <h2
          id="analysis-section-heading"
          className="mb-3 text-sm font-semibold text-muted-foreground"
        >
          AI 분석
        </h2>
        <SymbolAnalysisSection market={decodedMarket} code={decodedCode} />
      </section>
    </div>
  );
}
