/**
 * watchlist.ts — MSW handlers for /watchlist/* and /portfolio/* heatmap/calendar/insight
 *
 * Sprint-08 B-β/B-α 엔드포인트 stub.
 * 10종목 시드 (NVDA/AAPL/005930/005380/KRW-BTC/ETH-KRW/TSLA/NFLX/META/MSFT)
 */
import { http, HttpResponse } from "msw";

interface MockWatchlistItem {
  id: number;
  market: string;
  code: string;
  memo: string | null;
  created_at: string;
}

const WATCHLIST_ITEMS: MockWatchlistItem[] = [
  {
    id: 1,
    market: "yahoo",
    code: "NVDA",
    memo: "AI 반도체 대표 종목",
    created_at: "2026-04-19T00:00:00Z",
  },
  {
    id: 2,
    market: "yahoo",
    code: "AAPL",
    memo: "서비스 매출 모니터링",
    created_at: "2026-04-19T00:00:00Z",
  },
  {
    id: 3,
    market: "naver_kr",
    code: "005930.KS",
    memo: "국내 반도체 대형주",
    created_at: "2026-04-19T00:00:00Z",
  },
  {
    id: 4,
    market: "upbit",
    code: "KRW-BTC",
    memo: "디지털 자산 대표",
    created_at: "2026-04-19T00:00:00Z",
  },
];

const SYMBOL_RESULTS = [
  {
    symbol: "NVDA",
    name: "NVIDIA",
    asset_class: "stock",
    market: "yahoo",
    currency: "USD",
  },
  {
    symbol: "AAPL",
    name: "Apple",
    asset_class: "stock",
    market: "yahoo",
    currency: "USD",
  },
  {
    symbol: "005930.KS",
    name: "삼성전자",
    asset_class: "stock",
    market: "naver_kr",
    currency: "KRW",
  },
  {
    symbol: "KRW-BTC",
    name: "비트코인",
    asset_class: "crypto",
    market: "upbit",
    currency: "KRW",
  },
  {
    symbol: "KRW-ETH",
    name: "이더리움",
    asset_class: "crypto",
    market: "upbit",
    currency: "KRW",
  },
];

let watchlistItems: MockWatchlistItem[] = [...WATCHLIST_ITEMS];
let nextWatchlistId = 100;

// ---------- 워치리스트 summary ----------
export const watchlistSummaryHandler = http.get(/\/watchlist\/summary/, () => {
  return HttpResponse.json({
    watched_count: watchlistItems.length,
    up_avg_pct: "4.62",
    down_avg_pct: "-2.38",
    top_gainer_name: "삼성전자",
    top_gainer_pct: "+6.12",
  });
});

export const watchlistItemsHandler = http.get(
  /\/market\/watchlist\/items$/,
  () => HttpResponse.json(watchlistItems),
);

export const watchlistCreateItemHandler = http.post(
  /\/market\/watchlist\/items$/,
  async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const item = {
      id: nextWatchlistId++,
      market: String(body["market"] ?? "yahoo"),
      code: String(body["code"] ?? "NVDA"),
      memo: body["memo"] == null ? null : String(body["memo"]),
      created_at: new Date().toISOString(),
    };
    watchlistItems = [...watchlistItems, item];
    return HttpResponse.json(item, { status: 201 });
  },
);

export const watchlistDeleteItemHandler = http.delete(
  /\/market\/watchlist\/items\/\d+$/,
  ({ request }) => {
    const id = Number(new URL(request.url).pathname.split("/").pop());
    watchlistItems = watchlistItems.filter((item) => item.id !== id);
    return new HttpResponse(null, { status: 204 });
  },
);

export const symbolSearchHandler = http.get(
  /\/market\/symbols\/search/,
  ({ request }) => {
    const q = new URL(request.url).searchParams.get("q")?.toLowerCase() ?? "";
    const filtered = q
      ? SYMBOL_RESULTS.filter(
          (item) =>
            item.symbol.toLowerCase().includes(q) ||
            item.name.toLowerCase().includes(q),
        )
      : SYMBOL_RESULTS;
    return HttpResponse.json(filtered);
  },
);

// ---------- 인기 TOP 5 ----------
const POPULAR: object[] = [
  { rank: 1, ticker: "KRW-BTC", name: "비트코인", change_pct: "11.21" },
  { rank: 2, ticker: "NVDA", name: "NVIDIA", change_pct: "3.12" },
  { rank: 3, ticker: "AAPL", name: "Apple", change_pct: "2.05" },
  { rank: 4, ticker: "005930", name: "삼성전자", change_pct: "4.51" },
  { rank: 5, ticker: "META", name: "Meta", change_pct: "1.88" },
];

export const watchlistPopularHandler = http.get(/\/watchlist\/popular/, () => {
  return HttpResponse.json(POPULAR);
});

// ---------- 등락 TOP ----------
export const watchlistGainersLosersHandler = http.get(
  /\/watchlist\/gainers-losers/,
  () => {
    return HttpResponse.json({
      gainers: [
        { rank: 1, ticker: "005930", name: "삼성전자", change_pct: "6.12" },
        { rank: 2, ticker: "KRW-BTC", name: "비트코인", change_pct: "5.40" },
        { rank: 3, ticker: "NVDA", name: "NVIDIA", change_pct: "3.12" },
        { rank: 4, ticker: "TSLA", name: "Tesla", change_pct: "2.30" },
        { rank: 5, ticker: "AAPL", name: "Apple", change_pct: "2.05" },
      ],
      losers: [
        { rank: 1, ticker: "ETH-KRW", name: "이더리움", change_pct: "-3.85" },
        { rank: 2, ticker: "NFLX", name: "Netflix", change_pct: "-2.10" },
        { rank: 3, ticker: "005380", name: "현대차", change_pct: "-1.55" },
        { rank: 4, ticker: "MSFT", name: "Microsoft", change_pct: "-0.80" },
        { rank: 5, ticker: "META", name: "Meta", change_pct: "-0.22" },
      ],
    });
  },
);

let alertRules = [
  {
    id: 1,
    user_id: "demo",
    symbol: "NVDA",
    market: "yahoo",
    direction: "above",
    threshold: "520.0000",
    enabled: true,
    created_at: "2026-04-19T00:00:00Z",
  },
  {
    id: 2,
    user_id: "demo",
    symbol: "KRW-BTC",
    market: "upbit",
    direction: "below",
    threshold: "70000000.0000",
    enabled: false,
    created_at: "2026-04-19T00:00:00Z",
  },
];
let nextAlertId = 100;

export const watchlistAlertsListHandler = http.get(
  /\/watchlist\/alerts$/,
  () => HttpResponse.json(alertRules),
);

export const watchlistAlertsCreateHandler = http.post(
  /\/watchlist\/alerts$/,
  async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const alert = {
      id: nextAlertId++,
      user_id: "demo",
      symbol: String(body["symbol"] ?? "NVDA"),
      market: String(body["market"] ?? "yahoo"),
      direction: body["direction"] === "below" ? "below" : "above",
      threshold: Number(body["threshold"] ?? 0).toFixed(4),
      enabled: true,
      created_at: new Date().toISOString(),
    };
    alertRules = [...alertRules, alert];
    return HttpResponse.json(alert, { status: 201 });
  },
);

export const watchlistAlertsUpdateHandler = http.patch(
  /\/watchlist\/alerts\/\d+$/,
  async ({ request }) => {
    const id = Number(new URL(request.url).pathname.split("/").pop());
    const patch = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const current = alertRules.find((alert) => alert.id === id);
    if (!current) {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    const updated = {
      ...current,
      enabled:
        typeof patch["enabled"] === "boolean" ? patch["enabled"] : current.enabled,
      threshold:
        typeof patch["threshold"] === "number"
          ? patch["threshold"].toFixed(4)
          : current.threshold,
    };
    alertRules = alertRules.map((alert) => (alert.id === id ? updated : alert));
    return HttpResponse.json(updated);
  },
);

export const watchlistAlertsDeleteHandler = http.delete(
  /\/watchlist\/alerts\/\d+$/,
  ({ request }) => {
    const id = Number(new URL(request.url).pathname.split("/").pop());
    alertRules = alertRules.filter((alert) => alert.id !== id);
    return new HttpResponse(null, { status: 204 });
  },
);

// ---------- 섹터 히트맵 ----------
const SECTOR_TILES = [
  { sector: "Tech", weight_pct: "32.4", pnl_pct: "5.12", intensity: "0.51" },
  { sector: "Finance", weight_pct: "14.2", pnl_pct: "2.30", intensity: "0.23" },
  { sector: "Energy", weight_pct: "8.5", pnl_pct: "-1.20", intensity: "-0.12" },
  { sector: "Health", weight_pct: "11.0", pnl_pct: "3.40", intensity: "0.34" },
  { sector: "Consumer", weight_pct: "9.2", pnl_pct: "-3.10", intensity: "-0.31" },
  { sector: "Industrial", weight_pct: "7.3", pnl_pct: "1.05", intensity: "0.11" },
  { sector: "Utilities", weight_pct: "4.1", pnl_pct: "0.22", intensity: "0.02" },
  { sector: "RE", weight_pct: "3.5", pnl_pct: "-4.80", intensity: "-0.48" },
  { sector: "Materials", weight_pct: "5.2", pnl_pct: "4.20", intensity: "0.42" },
  { sector: "Telecom", weight_pct: "3.0", pnl_pct: "-0.50", intensity: "-0.05" },
];

export const portfolioSectorHeatmapHandler = http.get(
  /\/portfolio\/sectors\/heatmap/,
  () => {
    return HttpResponse.json(SECTOR_TILES);
  },
);

// ---------- 월간 수익률 달력 ----------
function buildMonthlyReturns(year: number): object[] {
  const result: object[] = [];
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const days = isLeap ? 366 : 365;
  for (let i = 0; i < days; i++) {
    const date = new Date(year, 0, 1 + i);
    const iso = date.toISOString().slice(0, 10);
    const ret = Math.sin(i * 0.3 + 1.2) * 3.5; // 결정론적 ±3.5%
    const absRet = Math.abs(ret);
    const level =
      absRet < 0.5 ? 0 : absRet < 1.5 ? 1 : absRet < 2.5 ? 2 : absRet < 3.5 ? 3 : 4;
    result.push({ date: iso, return_pct: ret.toFixed(2), cell_level: level });
  }
  return result;
}

export const portfolioMonthlyReturnsHandler = http.get(
  /\/portfolio\/monthly-returns/,
  ({ request }) => {
    const url = new URL(request.url);
    const year = Number(url.searchParams.get("year") ?? new Date().getFullYear());
    return HttpResponse.json(buildMonthlyReturns(year));
  },
);

// ---------- AI 인사이트 ----------
export const portfolioAiInsightHandler = http.get(
  /\/portfolio\/ai-insight/,
  () => {
    return HttpResponse.json({
      summary:
        "포트폴리오는 기술주(해외) 비중이 43.2%로 다소 집중되어 있으나, " +
        "NVIDIA와 AAPL의 강한 모멘텀이 전체 수익률을 지지하고 있습니다. " +
        "암호화폐 비중(18.8%)은 변동성 위험을 내포하지만 단기 상승세가 포트폴리오에 유리하게 작용 중입니다. " +
        "달러 강세 추세에 따라 환율 익스포저 관리가 중요한 시점입니다.",
      bullets: [
        "기술주 집중도 43.2% — 추가 분산을 위해 금융·헬스케어 섹터 검토 권장",
        "비트코인 +11.2% 기여로 단기 수익률 견인, 단 변동성 주의",
        "삼성전자 HBM 수주 긍정적 — 반도체 사이클 상승 수혜 예상",
      ],
      generated_at: new Date().toISOString(),
      stub_mode: true,
      gates: { schema: "pass", domain: "pass", critique: "pass" },
    });
  },
);

// ---------- 핸들러 통합 ----------
export const watchlistHandlers = [
  symbolSearchHandler,
  watchlistItemsHandler,
  watchlistCreateItemHandler,
  watchlistDeleteItemHandler,
  watchlistSummaryHandler,
  watchlistPopularHandler,
  watchlistGainersLosersHandler,
  watchlistAlertsListHandler,
  watchlistAlertsCreateHandler,
  watchlistAlertsUpdateHandler,
  watchlistAlertsDeleteHandler,
  portfolioSectorHeatmapHandler,
  portfolioMonthlyReturnsHandler,
  portfolioAiInsightHandler,
];
