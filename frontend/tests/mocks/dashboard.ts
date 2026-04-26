/**
 * dashboard.ts — MSW handlers for /portfolio/* and /search/news
 *
 * 대시보드 홈이 요구하는 6개 KPI + 비중 + 시계열 + TOP5 + 디멘션 + 뉴스를
 * 결정론적으로 채워준다. NEXT_PUBLIC_COPILOT_MOCK=1 동일 환경에서 활성화.
 */
import { http, HttpResponse } from "msw";

const SUMMARY = {
  user_id: "demo",
  total_value_krw: "18760000.00",
  total_cost_krw: "17905000.00",
  total_pnl_krw: "855000.00",
  total_pnl_pct: "4.77",
  daily_change_krw: "373088.00",
  daily_change_pct: "2.04",
  asset_class_breakdown: {
    stock_us: "0.4320",
    stock_kr: "0.2180",
    crypto: "0.1880",
    cash: "0.0920",
    fx: "0.0700",
  },
  holdings: [
    {
      id: 1,
      market: "yahoo",
      code: "AAPL",
      quantity: "12.00000000",
      avg_cost: "182.5000",
      currency: "USD",
      current_price: "212.8000",
      current_price_krw: "289500.00",
      value_krw: "3474000.00",
      cost_krw: "2982000.00",
      pnl_krw: "492000.00",
      pnl_pct: "16.50",
    },
    {
      id: 2,
      market: "yahoo",
      code: "NVDA",
      quantity: "6.00000000",
      avg_cost: "420.0000",
      currency: "USD",
      current_price: "512.4000",
      current_price_krw: "697000.00",
      value_krw: "4182000.00",
      cost_krw: "3423600.00",
      pnl_krw: "758400.00",
      pnl_pct: "22.15",
    },
    {
      id: 3,
      market: "naver_kr",
      code: "005930.KS",
      quantity: "40.00000000",
      avg_cost: "71000.0000",
      currency: "KRW",
      current_price: "74200.0000",
      current_price_krw: "74200.00",
      value_krw: "2968000.00",
      cost_krw: "2840000.00",
      pnl_krw: "128000.00",
      pnl_pct: "4.51",
    },
    {
      id: 4,
      market: "upbit",
      code: "KRW-BTC",
      quantity: "0.04200000",
      avg_cost: "66000000.0000",
      currency: "KRW",
      current_price: "73400000.0000",
      current_price_krw: "73400000.00",
      value_krw: "3082800.00",
      cost_krw: "2772000.00",
      pnl_krw: "310800.00",
      pnl_pct: "11.21",
    },
    {
      id: 5,
      market: "upbit",
      code: "KRW-ETH",
      quantity: "0.45000000",
      avg_cost: "4200000.0000",
      currency: "KRW",
      current_price: "4040000.0000",
      current_price_krw: "4040000.00",
      value_krw: "1818000.00",
      cost_krw: "1890000.00",
      pnl_krw: "-72000.00",
      pnl_pct: "-3.85",
    },
    {
      id: 6,
      market: "yahoo",
      code: "TSLA",
      quantity: "8.00000000",
      avg_cost: "195.0000",
      currency: "USD",
      current_price: "213.5000",
      current_price_krw: "290500.00",
      value_krw: "2324000.00",
      cost_krw: "2122000.00",
      pnl_krw: "202000.00",
      pnl_pct: "9.52",
    },
  ],
  holdings_count: 23,
  worst_asset_pct: "-3.85",
  risk_score_pct: "12.40",
  period_change_pct: "1.23",
  period_days: 30,
  dimension_breakdown: [
    { label: "stock_us", weight_pct: "43.20", pnl_pct: "15.80" },
    { label: "stock_kr", weight_pct: "21.80", pnl_pct: "4.51" },
    { label: "crypto", weight_pct: "18.80", pnl_pct: "5.12" },
    { label: "cash", weight_pct: "9.20", pnl_pct: "0.00" },
    { label: "fx", weight_pct: "7.00", pnl_pct: "-1.20" },
  ],
  // B-α 완료 후 BE 가 추가하는 필드. MSW 에서 미리 픽스처 제공.
  market_leaders: [
    {
      rank: 1,
      name: "NVIDIA",
      ticker: "NVDA",
      logo_url: null,
      price_display: "$512.40",
      change_pct: "3.12",
      change_krw: "₩4,420",
    },
    {
      rank: 2,
      name: "삼성전자",
      ticker: "005930",
      logo_url: null,
      price_display: "₩74,200",
      change_pct: "4.51",
      change_krw: null,
    },
    {
      rank: 3,
      name: "Bitcoin",
      ticker: "KRW-BTC",
      logo_url: null,
      price_display: "₩73.40M",
      change_pct: "11.21",
      change_krw: "₩7.36M",
    },
  ],
};

// period_days → (누적 수익률 %, 시작 평가액)
// 심사 시연 시 기간 탭 전환이 "살아 있음"을 보여주기 위해 구간별 다른 수치 반환.
const PERIOD_PROFILE: Record<number, { changePct: string; startKrw: number }> = {
  7: { changePct: "0.41", startKrw: 18_680_000 },
  30: { changePct: "1.23", startKrw: 18_530_000 },
  90: { changePct: "3.82", startKrw: 18_070_000 },
  365: { changePct: "12.70", startKrw: 16_645_000 },
};

function profileFor(periodDays: number): { changePct: string; startKrw: number } {
  return (
    PERIOD_PROFILE[periodDays] ?? {
      changePct: "1.23",
      startKrw: 18_530_000,
    }
  );
}

function buildSnapshots(days: number, startKrw: number): unknown[] {
  const end = 18_760_000;
  const step = (end - startKrw) / days;
  const now = new Date();
  const out: unknown[] = [];
  for (let i = 0; i <= days; i++) {
    const d = new Date(now);
    d.setDate(now.getDate() - (days - i));
    const iso = d.toISOString().slice(0, 10);
    // 약간의 요철을 주어 실제 시계열처럼 보이게
    const jitter = Math.sin(i / 3) * 120_000;
    const total = Math.round(startKrw + step * i + jitter);
    out.push({
      id: i + 1,
      user_id: "demo",
      snapshot_date: iso,
      total_value_krw: String(total),
      total_pnl_krw: String(total - startKrw),
      asset_class_breakdown: SUMMARY.asset_class_breakdown,
      holdings_detail: [],
      created_at: d.toISOString(),
    });
  }
  return out;
}

const NEWS_FIXTURES = [
  {
    doc_id: 101,
    chunk_id: 1,
    source_url: "https://finance.naver.com/news/nvda-record-high",
    title: "NVIDIA, AI 수요 호조에 사상 최고가 경신",
    published_at: "2026-04-22T05:10:00Z",
    excerpt: "엔비디아가 데이터센터 매출 기대감에 힘입어 사상 최고가를 기록했다.",
    score: 0.92,
    thumbnail_url: "https://picsum.photos/seed/nvda/120/120",
  },
  {
    doc_id: 102,
    chunk_id: 1,
    source_url: "https://www.bloomberg.com/news/aapl-services",
    title: "Apple, 서비스 매출 또 한 번 최고 기록",
    published_at: "2026-04-21T12:30:00Z",
    excerpt: "Apple의 서비스 부문이 전년 대비 14% 성장하며 신기록을 썼다.",
    score: 0.88,
    thumbnail_url: "https://picsum.photos/seed/aapl/120/120",
  },
  {
    doc_id: 103,
    chunk_id: 1,
    source_url: "https://www.coindesk.com/btc-etf-flow",
    title: "비트코인 현물 ETF로 하루 2.3억 달러 순유입",
    published_at: "2026-04-21T08:00:00Z",
    excerpt: "비트코인 현물 ETF에 자금 유입이 재개되며 시세를 지지하고 있다.",
    score: 0.81,
    thumbnail_url: "https://picsum.photos/seed/btc/120/120",
  },
  {
    doc_id: 104,
    chunk_id: 1,
    source_url: "https://www.reuters.com/markets/tsla-delivery",
    title: "Tesla, Q2 인도량 가이던스 상향",
    published_at: "2026-04-20T23:45:00Z",
    excerpt: "테슬라가 Q2 차량 인도 가이던스를 기존 대비 3% 상향 조정했다.",
    score: 0.74,
    thumbnail_url: "https://picsum.photos/seed/tsla/120/120",
  },
  {
    doc_id: 105,
    chunk_id: 1,
    source_url: "https://news.samsung.co.kr/hbm-order",
    title: "삼성전자, HBM3e 대규모 수주 공시",
    published_at: "2026-04-20T01:15:00Z",
    excerpt: "삼성전자가 주요 AI 반도체 업체로부터 HBM3e 대규모 수주를 공시했다.",
    score: 0.71,
    thumbnail_url: "https://picsum.photos/seed/samsung/120/120",
  },
];

export const portfolioSummaryHandler = http.get(
  /\/portfolio\/summary/,
  ({ request }) => {
    const url = new URL(request.url);
    const periodDays = Number(url.searchParams.get("period_days") ?? 30);
    const { changePct } = profileFor(periodDays);
    return HttpResponse.json({
      ...SUMMARY,
      period_days: periodDays,
      period_change_pct: changePct,
    });
  },
);

export const portfolioSnapshotsHandler = http.get(
  /\/portfolio\/snapshots/,
  ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get("from");
    const to = url.searchParams.get("to");
    // from/to 가 주어지면 일수로 환산 (대시보드 페이지가 period_days 만큼 전 날짜를 보냄).
    // 그 외엔 기본 30일.
    let days = 30;
    if (from && to) {
      const diff = Math.round(
        (new Date(to).getTime() - new Date(from).getTime()) /
          (1000 * 60 * 60 * 24),
      );
      if (diff > 0) days = diff;
    }
    const { startKrw } = profileFor(days);
    return HttpResponse.json(buildSnapshots(days, startKrw));
  },
);

export const searchNewsHandler = http.get(/\/search\/news/, ({ request }) => {
  const url = new URL(request.url);
  const k = Number(url.searchParams.get("k") ?? 5);
  return HttpResponse.json(NEWS_FIXTURES.slice(0, Math.max(1, Math.min(k, NEWS_FIXTURES.length))));
});

export const dashboardHandlers = [
  portfolioSummaryHandler,
  portfolioSnapshotsHandler,
  searchNewsHandler,
];
