/**
 * MSW handlers for /market/* endpoints.
 *
 * Keep these fixtures aligned with backend response models. Several market
 * widgets render directly from these fields in browser mock mode.
 */
import { http, HttpResponse } from "msw";

export const MARKET_INDICES = [
  {
    ticker: "^KS11",
    display_name: "KOSPI",
    value: "2,705.32",
    change_pct: "+1.24",
    change_abs: "+33.01",
    sparkline_7d: [2645, 2658, 2672, 2680, 2668, 2690, 2705],
  },
  {
    ticker: "^KQ11",
    display_name: "KOSDAQ",
    value: "864.72",
    change_pct: "-0.38",
    change_abs: "-3.29",
    sparkline_7d: [870, 875, 868, 872, 865, 862, 864],
  },
  {
    ticker: "^GSPC",
    display_name: "S&P 500",
    value: "5,306.04",
    change_pct: "+0.57",
    change_abs: "+30.08",
    sparkline_7d: [5260, 5275, 5288, 5270, 5295, 5300, 5306],
  },
  {
    ticker: "^IXIC",
    display_name: "NASDAQ",
    value: "18,720.02",
    change_pct: "+0.84",
    change_abs: "+156.20",
    sparkline_7d: [18500, 18580, 18620, 18560, 18650, 18700, 18720],
  },
  {
    ticker: "^DJI",
    display_name: "DOW",
    value: "38,972.86",
    change_pct: "-0.21",
    change_abs: "-81.76",
    sparkline_7d: [39100, 39050, 38980, 39020, 38950, 38940, 38972],
  },
  {
    ticker: "^VIX",
    display_name: "VIX",
    value: "18.34",
    change_pct: "+5.12",
    change_abs: "+0.89",
    sparkline_7d: [16.2, 16.8, 17.5, 18.1, 17.8, 18.0, 18.34],
  },
  {
    ticker: "USDKRW",
    display_name: "USD/KRW",
    value: "1,389.63",
    change_pct: "+0.32",
    change_abs: "+4.44",
    sparkline_7d: [1382, 1385, 1387, 1384, 1388, 1390, 1389],
  },
];

export const MARKET_SECTORS = [
  { name: "Technology", change_pct: "+1.85", constituents: 75, leaders: ["AAPL", "MSFT", "NVDA"] },
  { name: "Healthcare", change_pct: "+0.42", constituents: 60, leaders: ["JNJ", "PFE", "UNH"] },
  { name: "Financials", change_pct: "-0.31", constituents: 65, leaders: ["JPM", "BAC", "GS"] },
  { name: "Consumer Disc.", change_pct: "+0.95", constituents: 54, leaders: ["AMZN", "TSLA", "HD"] },
  { name: "Industrials", change_pct: "+0.18", constituents: 72, leaders: ["HON", "GE", "MMM"] },
  { name: "Communication", change_pct: "+1.24", constituents: 28, leaders: ["GOOGL", "META", "VZ"] },
  { name: "Consumer Staples", change_pct: "-0.55", constituents: 38, leaders: ["PG", "KO", "WMT"] },
  { name: "Energy", change_pct: "-1.20", constituents: 28, leaders: ["XOM", "CVX", "COP"] },
  { name: "Utilities", change_pct: "+0.08", constituents: 29, leaders: ["NEE", "DUK", "SO"] },
  { name: "Real Estate", change_pct: "-0.72", constituents: 31, leaders: ["PLD", "AMT", "EQIX"] },
  { name: "Materials", change_pct: "+0.33", constituents: 25, leaders: ["LIN", "APD", "SHW"] },
];

export const MARKET_COMMODITIES = [
  {
    symbol: "CL=F",
    name: "원유(WTI)",
    price: "78.42",
    unit: "USD/배럴",
    change_pct: "-0.85",
  },
  {
    symbol: "GC=F",
    name: "금",
    price: "2,342.10",
    unit: "USD/온스",
    change_pct: "+0.54",
  },
  {
    symbol: "SI=F",
    name: "은",
    price: "27.85",
    unit: "USD/온스",
    change_pct: "+0.91",
  },
  {
    symbol: "HG=F",
    name: "구리",
    price: "4.56",
    unit: "USD/파운드",
    change_pct: "-0.22",
  },
  {
    symbol: "NG=F",
    name: "천연가스",
    price: "2.14",
    unit: "USD/MMBtu",
    change_pct: "-1.38",
  },
];

export const MARKET_WORLD_HEATMAP = [
  { country_code: "KR", country_name: "한국", change_pct: "+0.84", market_cap_usd: "$1.8T" },
  { country_code: "JP", country_name: "일본", change_pct: "+0.92", market_cap_usd: "$5.4T" },
  { country_code: "CN", country_name: "중국", change_pct: "-0.34", market_cap_usd: "$8.1T" },
  { country_code: "US", country_name: "미국", change_pct: "+0.71", market_cap_usd: "$46.2T" },
  { country_code: "GB", country_name: "영국", change_pct: "-0.18", market_cap_usd: "$2.9T" },
  { country_code: "DE", country_name: "독일", change_pct: "+0.61", market_cap_usd: "$2.1T" },
  { country_code: "BR", country_name: "브라질", change_pct: "-0.95", market_cap_usd: "$0.7T" },
  { country_code: "IN", country_name: "인도", change_pct: "+1.20", market_cap_usd: "$3.9T" },
];

export const MARKET_NEWS = [
  {
    id: "mn1",
    title: "연준, 금리 동결 이후 인플레이션 지표 주목",
    source: "Reuters",
    published_at: new Date(Date.now() - 3600000).toISOString(),
    url: "#",
    sentiment: "neutral",
  },
  {
    id: "mn2",
    title: "엔비디아 실적 호조로 AI 반도체 수요 기대 확대",
    source: "Bloomberg",
    published_at: new Date(Date.now() - 7200000).toISOString(),
    url: "#",
    sentiment: "positive",
  },
  {
    id: "mn3",
    title: "중국 PMI 예상 하회로 글로벌 경기 둔화 우려",
    source: "Yonhap",
    published_at: new Date(Date.now() - 10800000).toISOString(),
    url: "#",
    sentiment: "negative",
  },
  {
    id: "mn4",
    title: "KOSPI, 외국인 순매수에 2700선 회복 시도",
    source: "Hankyung",
    published_at: new Date(Date.now() - 14400000).toISOString(),
    url: "#",
    sentiment: "positive",
  },
];

function quoteFor(market: string, code: string) {
  if (market === "upbit") {
    return {
      symbol: code,
      market,
      price: 120000000,
      change: 1000000,
      change_pct: 0.84,
      currency: "KRW",
      volume: 1220,
      timestamp: "2026-04-30T00:00:00Z",
    };
  }
  return {
    symbol: code,
    market,
    price: code === "NVDA" ? 697 : 192.5,
    change: code === "NVDA" ? 8.4 : 1.5,
    change_pct: code === "NVDA" ? 1.22 : 0.78,
    currency: "USD",
    volume: 50_000_000,
    timestamp: "2026-04-30T00:00:00Z",
  };
}

function buildOhlc(market: string, code: string) {
  const base = market === "upbit" ? 115000000 : code === "NVDA" ? 650 : 188;
  return Array.from({ length: 90 }, (_, index) => {
    const step = market === "upbit" ? 200000 : 0.6;
    const close = base + index * step;
    return {
      ts: new Date(Date.now() - (89 - index) * 24 * 60 * 60 * 1000).toISOString(),
      open: close - step * 0.6,
      high: close + step * 1.2,
      low: close - step * 1.4,
      close,
      volume: market === "upbit" ? 1000 + index * 10 : 45_000_000 + index * 250_000,
    };
  });
}

function buildIndicators(market: string, code: string) {
  const ohlc = buildOhlc(market, code);
  const rsi_14 = ohlc.slice(-60).map((bar, index) => ({
    t: bar.ts,
    v: 48 + Math.sin(index / 5) * 9,
  }));
  const macd = ohlc.slice(-60).map((bar, index) => ({
    t: bar.ts,
    macd: Math.sin(index / 8) * 1.4,
    signal: Math.sin(index / 8) * 1.1,
    histogram: Math.sin(index / 8) * 0.3,
  }));
  const bollingerMid = ohlc.slice(-60).map((bar) => ({ t: bar.ts, v: Number(bar.close) }));
  return {
    interval: "day",
    period: 60,
    rsi_14,
    macd,
    bollinger: {
      upper: bollingerMid.map((point) => ({ t: point.t, v: point.v * 1.04 })),
      mid: bollingerMid,
      lower: bollingerMid.map((point) => ({ t: point.t, v: point.v * 0.96 })),
    },
    stochastic: ohlc.slice(-60).map((bar, index) => ({
      t: bar.ts,
      k: 55 + Math.sin(index / 6) * 14,
      d: 52 + Math.sin(index / 7) * 10,
    })),
    metrics: {
      rsi_latest: 57.4,
      macd_latest: 1.2,
      macd_signal: 0.9,
      bollinger_position: 0.62,
    },
    signal: "hold",
  };
}

function analyzeResponseFor(market: string, code: string, includePortfolioContext: boolean) {
  return {
    request_id: `msw-analyze-${market}-${code}`,
    status: "ok",
    result: {
      asset_class: market === "upbit" ? "crypto" : "stock",
      headline: includePortfolioContext
        ? `${code} 보유 맥락 반영 분석`
        : `${code} 시장 데이터 기반 분석`,
      narrative: includePortfolioContext
        ? "현재 보유 비중과 평가손익을 함께 고려한 참고용 분석입니다."
        : "가격, 거래량, 기술 지표를 기반으로 한 모의 분석입니다.",
      summary: `${code} 분석 요약`,
      highlights: ["추세는 중립 구간에서 긍정 신호가 있습니다.", "단기 변동성 관리는 필요합니다."],
      metrics: includePortfolioContext
        ? {
            latest_close: quoteFor(market, code).price,
            matched_holding: {
              market,
              code,
              quantity: market === "upbit" ? "0.15" : "5",
              avg_cost: market === "upbit" ? "97000000" : "185",
              currency: market === "upbit" ? "KRW" : "USD",
              pnl_pct: 4.1,
            },
          }
        : { latest_close: quoteFor(market, code).price },
      signals: [{ kind: "trend", strength: "medium", rationale: "모의 지표 기준 중립 이상" }],
      evidence: [{ claim: "최근 가격 흐름과 기술 지표 모의값", source: "market.mock", rows: [0] }],
      confidence: 0.78,
    },
    meta: {
      asset_class: market === "upbit" ? "crypto" : "stock",
      router_reason: `${market}/${code} 심볼과 모의 응답`,
      gates: { schema_gate: "pass", domain_gate: "pass", critique_gate: "pass" },
      latency_ms: 120,
      analyzer_name: market === "upbit" ? "crypto" : "stock",
      evidence_snippets: ["market quote fixture", "indicator fixture"],
    },
  };
}

export const marketHandlers = [
  http.get("http://localhost:8000/market/indices", () =>
    HttpResponse.json(MARKET_INDICES),
  ),
  http.get("http://localhost:8000/market/sectors", () =>
    HttpResponse.json(MARKET_SECTORS),
  ),
  http.get("http://localhost:8000/market/commodities", () =>
    HttpResponse.json(MARKET_COMMODITIES),
  ),
  http.get("http://localhost:8000/market/world-heatmap", () =>
    HttpResponse.json(MARKET_WORLD_HEATMAP),
  ),
  http.get("http://localhost:8000/market/news", () =>
    HttpResponse.json(MARKET_NEWS),
  ),
  http.get(/\/market\/quotes\/[^/]+\/[^/?]+$/, ({ request }) => {
    const [, , , market, code] = new URL(request.url).pathname.split("/");
    return HttpResponse.json(quoteFor(decodeURIComponent(market ?? ""), decodeURIComponent(code ?? "")));
  }),
  http.get(/\/market\/ohlc\/[^/]+\/[^/?]+$/, ({ request }) => {
    const [, , , market, code] = new URL(request.url).pathname.split("/");
    return HttpResponse.json(buildOhlc(decodeURIComponent(market ?? ""), decodeURIComponent(code ?? "")));
  }),
  http.get(/\/market\/symbol\/[^/]+\/[^/]+\/indicators$/, ({ request }) => {
    const [, , , market, code] = new URL(request.url).pathname.split("/");
    return HttpResponse.json(buildIndicators(decodeURIComponent(market ?? ""), decodeURIComponent(code ?? "")));
  }),
  http.post("http://localhost:8000/analyze", async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as {
      symbol?: { market?: string; code?: string };
      include_portfolio_context?: boolean;
    };
    const market = body.symbol?.market ?? "yahoo";
    const code = body.symbol?.code ?? "AAPL";
    return HttpResponse.json(
      analyzeResponseFor(market, code, body.include_portfolio_context ?? false),
    );
  }),
];
