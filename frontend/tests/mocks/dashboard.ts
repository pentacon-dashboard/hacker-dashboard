/**
 * dashboard.ts — MSW handlers for /portfolio/* and /search/news
 *
 * 대시보드 홈이 요구하는 6개 KPI + 비중 + 시계열 + TOP5 + 디멘션 + 뉴스를
 * 결정론적으로 채워준다. NEXT_PUBLIC_COPILOT_MOCK=1 동일 환경에서 활성화.
 */
import { http, HttpResponse } from "msw";

const SUMMARY = {
  user_id: "demo",
  client_id: "client-001",
  client_name: "고객 A",
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

const CLIENT_SUMMARIES: Record<string, typeof SUMMARY> = {
  "client-001": SUMMARY,
  "client-002": {
    ...SUMMARY,
    client_id: "client-002",
    client_name: "고객 B",
    total_value_krw: "12450000.00",
    total_cost_krw: "12800000.00",
    total_pnl_krw: "-350000.00",
    total_pnl_pct: "-2.73",
    daily_change_krw: "-82000.00",
    daily_change_pct: "-0.66",
    asset_class_breakdown: {
      stock_kr: "0.3600",
      stock_us: "0.2800",
      crypto: "0.1000",
      cash: "0.2200",
      fx: "0.0400",
    },
    holdings: SUMMARY.holdings.slice(0, 4).map((holding, index) => ({
      ...holding,
      id: index + 101,
      pnl_pct: index === 0 ? "-4.20" : holding.pnl_pct,
    })),
    holdings_count: 4,
    worst_asset_pct: "-4.20",
    risk_score_pct: "38.60",
    dimension_breakdown: [
      { label: "stock_kr", weight_pct: "36.00", pnl_pct: "-1.80" },
      { label: "stock_us", weight_pct: "28.00", pnl_pct: "2.10" },
      { label: "cash", weight_pct: "22.00", pnl_pct: "0.00" },
      { label: "crypto", weight_pct: "10.00", pnl_pct: "-4.20" },
      { label: "fx", weight_pct: "4.00", pnl_pct: "0.40" },
    ],
  },
};

const CLIENT_A_SUMMARY = CLIENT_SUMMARIES["client-001"]!;
const CLIENT_B_SUMMARY = CLIENT_SUMMARIES["client-002"]!;

const CLIENTS = [
  {
    client_id: "client-001",
    client_name: "고객 A",
    aum_krw: CLIENT_A_SUMMARY.total_value_krw,
    holdings_count: CLIENT_A_SUMMARY.holdings_count,
    risk_grade: "low",
    risk_score_pct: CLIENT_A_SUMMARY.risk_score_pct,
    total_pnl_pct: CLIENT_A_SUMMARY.total_pnl_pct,
  },
  {
    client_id: "client-002",
    client_name: "고객 B",
    aum_krw: CLIENT_B_SUMMARY.total_value_krw,
    holdings_count: CLIENT_B_SUMMARY.holdings_count,
    risk_grade: "medium",
    risk_score_pct: CLIENT_B_SUMMARY.risk_score_pct,
    total_pnl_pct: CLIENT_B_SUMMARY.total_pnl_pct,
  },
];

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

function summaryFor(clientId: string) {
  return (
    CLIENT_SUMMARIES[clientId] ?? {
      ...SUMMARY,
      client_id: clientId,
      client_name: clientId,
      total_value_krw: "0.00",
      total_cost_krw: "0.00",
      total_pnl_krw: "0.00",
      total_pnl_pct: "0.00",
      daily_change_krw: "0.00",
      daily_change_pct: "0.00",
      asset_class_breakdown: {},
      holdings: [],
      holdings_count: 0,
      worst_asset_pct: "0.00",
      risk_score_pct: "0.00",
      dimension_breakdown: [],
    }
  );
}

function buildSnapshots(days: number, startKrw: number, clientId: string): unknown[] {
  const summary = summaryFor(clientId);
  const end = Number(summary.total_value_krw);
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
      client_id: summary.client_id,
      client_name: summary.client_name,
      snapshot_date: iso,
      total_value_krw: String(total),
      total_pnl_krw: String(total - startKrw),
      asset_class_breakdown: summary.asset_class_breakdown,
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

export const portfolioClientsHandler = http.get(/\/portfolio\/clients/, () => {
  const totalAum = CLIENTS.reduce((sum, client) => sum + Number(client.aum_krw), 0);
  return HttpResponse.json({
    user_id: "demo",
    aum_krw: totalAum.toFixed(2),
    client_count: CLIENTS.length,
    clients: CLIENTS,
  });
});

export const portfolioHoldingsHandler = http.get(/\/portfolio\/holdings$/, ({ request }) => {
  const url = new URL(request.url);
  const clientId = url.searchParams.get("client_id") ?? "client-001";
  const summary = summaryFor(clientId);
  return HttpResponse.json(
    summary.holdings.map((holding) => ({
      id: holding.id,
      user_id: "demo",
      client_id: summary.client_id,
      market: holding.market,
      code: holding.code,
      quantity: holding.quantity,
      avg_cost: holding.avg_cost,
      currency: holding.currency,
      created_at: "2026-04-19T00:00:00Z",
      updated_at: "2026-04-19T00:00:00Z",
    })),
  );
});

export const portfolioCreateHoldingHandler = http.post(/\/portfolio\/holdings$/, async ({ request }) => {
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  return HttpResponse.json(
    {
      id: 999,
      user_id: "demo",
      client_id: body["client_id"] ?? "client-001",
      market: body["market"] ?? "upbit",
      code: body["code"] ?? "KRW-BTC",
      quantity: body["quantity"] ?? "0",
      avg_cost: body["avg_cost"] ?? "0",
      currency: body["currency"] ?? "KRW",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    { status: 201 },
  );
});

export const portfolioSummaryHandler = http.get(
  /\/portfolio\/summary/,
  ({ request }) => {
    const url = new URL(request.url);
    const periodDays = Number(url.searchParams.get("period_days") ?? 30);
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    const summary = summaryFor(clientId);
    const { changePct } = profileFor(periodDays);
    return HttpResponse.json({
      ...summary,
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
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    const { startKrw } = profileFor(days);
    const scale = Number(summaryFor(clientId).total_value_krw) / Number(SUMMARY.total_value_krw);
    return HttpResponse.json(buildSnapshots(days, Math.round(startKrw * scale), clientId));
  },
);

export const portfolioSectorHeatmapHandler = http.get(
  /\/portfolio\/sectors\/heatmap/,
  ({ request }) => {
    const url = new URL(request.url);
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    if (clientId === "client-002") {
      return HttpResponse.json([
        { sector: "KR Equity", weight_pct: "36.00", pnl_pct: "-1.80", intensity: "-0.18" },
        { sector: "US Equity", weight_pct: "28.00", pnl_pct: "2.10", intensity: "0.21" },
        { sector: "Cash", weight_pct: "22.00", pnl_pct: "0.00", intensity: "0.00" },
        { sector: "Crypto", weight_pct: "10.00", pnl_pct: "-4.20", intensity: "-0.42" },
      ]);
    }
    return HttpResponse.json([
      { sector: "Tech", weight_pct: "43.20", pnl_pct: "15.80", intensity: "0.80" },
      { sector: "KR Equity", weight_pct: "21.80", pnl_pct: "4.51", intensity: "0.45" },
      { sector: "Crypto", weight_pct: "18.80", pnl_pct: "5.12", intensity: "0.51" },
      { sector: "Cash", weight_pct: "9.20", pnl_pct: "0.00", intensity: "0.00" },
    ]);
  },
);

function buildMonthlyReturns(year: number, clientId: string): object[] {
  const result: object[] = [];
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const days = isLeap ? 366 : 365;
  const phase = clientId === "client-002" ? 2.4 : 1.2;
  for (let i = 0; i < days; i++) {
    const date = new Date(year, 0, 1 + i);
    const iso = date.toISOString().slice(0, 10);
    const ret = Math.sin(i * 0.3 + phase) * 3.5;
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
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    return HttpResponse.json(buildMonthlyReturns(year, clientId));
  },
);

export const portfolioAiInsightHandler = http.get(
  /\/portfolio\/ai-insight/,
  ({ request }) => {
    const url = new URL(request.url);
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    return HttpResponse.json({
      summary:
        clientId === "client-002"
          ? "고객 B는 암호화폐 비중이 낮고 현금 여력이 있는 방어형 포트폴리오입니다."
          : "고객 A는 해외주식과 암호화폐 비중이 높은 성장형 포트폴리오입니다.",
      bullets:
        clientId === "client-002"
          ? ["부진한 암호화폐 노출을 점검하세요.", "현금 비중이 있어 분할 재진입 여력이 있습니다."]
          : ["해외주식 노출이 주요 수익 기여 요인입니다.", "암호화폐 변동성은 지속적으로 모니터링해야 합니다."],
      generated_at: new Date().toISOString(),
      stub_mode: true,
      gates: { schema: "pass", domain: "pass", critique: "pass" },
    });
  },
);

function normalizeAllocation(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== "object") {
    return { stock_kr: 0.2, stock_us: 0.4, crypto: 0.3, cash: 0.1, fx: 0 };
  }
  const input = raw as Record<string, unknown>;
  return {
    stock_kr: Number(input["stock_kr"] ?? 0),
    stock_us: Number(input["stock_us"] ?? 0),
    crypto: Number(input["crypto"] ?? 0),
    cash: Number(input["cash"] ?? 0),
    fx: Number(input["fx"] ?? 0),
  };
}

export const portfolioRebalanceHandler = http.post(
  /\/portfolio\/rebalance/,
  async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const clientId = String(body["client_id"] ?? "client-001");
    const targetAllocation = normalizeAllocation(body["target_allocation"]);
    const currentAllocation =
      clientId === "client-002"
        ? { stock_kr: 0.36, stock_us: 0.28, crypto: 0.1, cash: 0.22, fx: 0.04 }
        : { stock_kr: 0.218, stock_us: 0.432, crypto: 0.188, cash: 0.092, fx: 0.07 };
    const drift = Object.fromEntries(
      Object.entries(targetAllocation).map(([key, value]) => [
        key,
        Math.round((value - (currentAllocation[key as keyof typeof currentAllocation] ?? 0)) * 10000) / 10000,
      ]),
    );

    return HttpResponse.json({
      request_id: `msw-rebalance-${clientId}`,
      status: "ok",
      current_allocation: currentAllocation,
      target_allocation: targetAllocation,
      drift,
      actions: [
        {
          action: "sell",
          market: "upbit",
          code: clientId === "client-002" ? "KRW-ETH" : "KRW-BTC",
          asset_class: "crypto",
          quantity: clientId === "client-002" ? "0.12" : "0.01",
          estimated_value_krw: clientId === "client-002" ? "520000" : "734000",
          reason: "목표 비중 대비 암호화폐 비중이 높아 일부 축소합니다.",
        },
        {
          action: "buy",
          market: "yahoo",
          code: clientId === "client-002" ? "AAPL" : "NVDA",
          asset_class: "stock_us",
          quantity: clientId === "client-002" ? "2" : "1",
          estimated_value_krw: clientId === "client-002" ? "579000" : "697000",
          reason: "목표 비중 대비 해외주식 비중을 보강합니다.",
        },
      ],
      expected_allocation: targetAllocation,
      summary: {
        total_trades: 2,
        total_sell_value_krw: clientId === "client-002" ? "520000" : "734000",
        total_buy_value_krw: clientId === "client-002" ? "579000" : "697000",
        rebalance_cost_estimate_krw: "3500",
      },
      llm_analysis: {
        headline: "목표 비중에 맞춘 리밸런싱 제안",
        narrative:
          "결정론적 비중 차이를 기준으로 과대 노출 자산을 줄이고 부족한 자산군을 보강하는 제안입니다.",
        warnings: ["거래 전 세금, 수수료, 고객 투자성향을 PB가 최종 확인해야 합니다."],
        confidence: 0.82,
      },
      meta: {
        latency_ms: 120,
        gates: { schema: "pass", domain: "pass", critique: "pass" },
        evidence_snippets: [
          `${clientId} deterministic allocation drift`,
          "target_allocation request body",
        ],
      },
    });
  },
);

export const searchNewsHandler = http.get(/\/search\/news/, ({ request }) => {
  const url = new URL(request.url);
  const k = Number(url.searchParams.get("k") ?? 5);
  return HttpResponse.json(NEWS_FIXTURES.slice(0, Math.max(1, Math.min(k, NEWS_FIXTURES.length))));
});

export const portfolioMarketLeadersHandler = http.get(
  /\/portfolio\/market-leaders/,
  ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get("limit") ?? 5);
    const rows = [
      {
        rank: 1,
        name: "NVIDIA",
        ticker: "NVDA",
        market: "yahoo",
        price: "512.40",
        currency: "USD",
        logo_url: null,
        price_display: "$512.40",
        change_pct: "3.12",
        change_krw: "+4,420",
      },
      {
        rank: 2,
        name: "삼성전자",
        ticker: "005930",
        market: "naver_kr",
        price: "74200",
        currency: "KRW",
        logo_url: null,
        price_display: "₩74,200",
        change_pct: "4.51",
        change_krw: null,
      },
      {
        rank: 3,
        name: "Bitcoin",
        ticker: "KRW-BTC",
        market: "upbit",
        price: "73400000",
        currency: "KRW",
        logo_url: null,
        price_display: "₩73.40M",
        change_pct: "11.21",
        change_krw: "+₩7.36M",
      },
      {
        rank: 4,
        name: "Apple",
        ticker: "AAPL",
        market: "yahoo",
        price: "212.80",
        currency: "USD",
        logo_url: null,
        price_display: "$212.80",
        change_pct: "1.88",
        change_krw: "+2,900",
      },
      {
        rank: 5,
        name: "Tesla",
        ticker: "TSLA",
        market: "yahoo",
        price: "213.50",
        currency: "USD",
        logo_url: null,
        price_display: "$213.50",
        change_pct: "0.74",
        change_krw: "+1,120",
      },
    ];
    return HttpResponse.json(rows.slice(0, Math.max(1, Math.min(limit, rows.length))));
  },
);

export const dashboardHandlers = [
  portfolioClientsHandler,
  portfolioHoldingsHandler,
  portfolioCreateHoldingHandler,
  portfolioSummaryHandler,
  portfolioSnapshotsHandler,
  portfolioSectorHeatmapHandler,
  portfolioMonthlyReturnsHandler,
  portfolioAiInsightHandler,
  portfolioRebalanceHandler,
  portfolioMarketLeadersHandler,
  searchNewsHandler,
];
