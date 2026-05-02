import { expect, type Page, type Route } from "@playwright/test";

const HOLDINGS = [
  {
    id: 1,
    user_id: "pb-demo",
    client_id: "client-001",
    market: "upbit",
    code: "KRW-BTC",
    quantity: "0.05000000",
    avg_cost: "85000000.0000",
    currency: "KRW",
    current_price: "95000000.0000",
    current_price_krw: "95000000.00",
    value_krw: "4750000.00",
    cost_krw: "4250000.00",
    pnl_krw: "500000.00",
    pnl_pct: "11.76",
    asset_class: "crypto",
    created_at: "2026-04-01T00:00:00Z",
    updated_at: "2026-04-19T00:00:00Z",
  },
  {
    id: 2,
    user_id: "pb-demo",
    client_id: "client-001",
    market: "yahoo",
    code: "AAPL",
    quantity: "5.00000000",
    avg_cost: "185.0000",
    currency: "USD",
    current_price: "192.5000",
    current_price_krw: "259875.00",
    value_krw: "1299375.00",
    cost_krw: "1248750.00",
    pnl_krw: "50625.00",
    pnl_pct: "4.05",
    asset_class: "stock_us",
    created_at: "2026-04-01T00:00:00Z",
    updated_at: "2026-04-19T00:00:00Z",
  },
];

const CLIENTS = [
  {
    client_id: "client-001",
    client_name: "Client A",
    aum_krw: "6049375.00",
    holdings_count: 2,
    risk_grade: "medium",
    risk_score_pct: "42.00",
    total_pnl_pct: "10.05",
  },
  {
    client_id: "client-002",
    client_name: "Client B",
    aum_krw: "3200000.00",
    holdings_count: 1,
    risk_grade: "low",
    risk_score_pct: "18.00",
    total_pnl_pct: "-1.20",
  },
];

const AAPL_QUOTE = {
  symbol: "AAPL",
  market: "yahoo",
  price: 192.5,
  change: 1.5,
  change_pct: 0.78,
  currency: "USD",
  volume: 50000000,
  timestamp: "2026-04-20T12:00:00Z",
};

const BTC_QUOTE = {
  symbol: "KRW-BTC",
  market: "upbit",
  price: 120000000,
  change: 1000000,
  change_pct: 0.84,
  currency: "KRW",
  volume: 1200,
  timestamp: "2026-04-19T12:00:00Z",
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function summaryFor(clientId: string, empty = false) {
  const holdings = empty ? [] : HOLDINGS.map((holding) => ({ ...holding, client_id: clientId }));
  const totalValue = holdings.reduce((sum, holding) => sum + Number(holding.value_krw), 0);
  const totalCost = holdings.reduce((sum, holding) => sum + Number(holding.cost_krw), 0);
  const totalPnl = totalValue - totalCost;

  return {
    user_id: "pb-demo",
    client_id: clientId,
    client_name: clientId === "client-002" ? "Client B" : "Client A",
    total_value_krw: totalValue.toFixed(2),
    total_cost_krw: totalCost.toFixed(2),
    total_pnl_krw: totalPnl.toFixed(2),
    total_pnl_pct: totalCost > 0 ? ((totalPnl / totalCost) * 100).toFixed(2) : "0.00",
    daily_change_krw: empty ? "0.00" : "150000.00",
    daily_change_pct: empty ? "0.00" : "1.00",
    asset_class_breakdown: empty
      ? {}
      : { stock_kr: "0.00", stock_us: "0.21", crypto: "0.79", cash: "0.00", fx: "0.00" },
    holdings,
    holdings_count: holdings.length,
    worst_asset_pct: empty ? "0.00" : "4.05",
    risk_score_pct: empty ? "0.00" : "42.00",
    period_change_pct: empty ? "0.00" : "1.23",
    period_days: 30,
    dimension_breakdown: empty
      ? []
      : [
          { label: "crypto", weight_pct: "79.00", pnl_pct: "11.76" },
          { label: "stock_us", weight_pct: "21.00", pnl_pct: "4.05" },
        ],
  };
}

function ohlcFor(base: number) {
  return Array.from({ length: 80 }, (_, index) => ({
    ts: new Date(Date.UTC(2026, 2, 1 + index)).toISOString(),
    open: base + index * 10,
    high: base + index * 10 + 25,
    low: base + index * 10 - 25,
    close: base + index * 10 + 5,
    volume: 1000 + index * 10,
  }));
}

function indicators() {
  const rsi_14 = Array.from({ length: 40 }, (_, index) => ({
    t: new Date(Date.UTC(2026, 3, index + 1)).toISOString(),
    v: 45 + Math.sin(index / 4) * 10,
  }));
  const macd = Array.from({ length: 40 }, (_, index) => ({
    t: new Date(Date.UTC(2026, 3, index + 1)).toISOString(),
    macd: Math.sin(index / 5),
    signal: Math.sin(index / 6),
    hist: Math.sin(index / 5) - Math.sin(index / 6),
  }));

  return {
    interval: "day",
    period: 60,
    rsi_14,
    macd,
    bollinger: {
      upper: rsi_14.map((point) => ({ t: point.t, v: 210 })),
      mid: rsi_14.map((point) => ({ t: point.t, v: 200 })),
      lower: rsi_14.map((point) => ({ t: point.t, v: 190 })),
    },
    stochastic: rsi_14.map((point) => ({ t: point.t, k: 52, d: 48 })),
    metrics: {
      rsi_latest: 55,
      macd_latest: 0.8,
      macd_signal: 0.5,
      bollinger_position: 0.6,
    },
    signal: "hold",
  };
}

export async function mockPortfolioApis(
  page: Page,
  options: { empty?: boolean } = {},
) {
  await page.route("**/portfolio/clients**", (route) =>
    json(route, {
      user_id: "pb-demo",
      aum_krw: CLIENTS.reduce((sum, client) => sum + Number(client.aum_krw), 0).toFixed(2),
      client_count: CLIENTS.length,
      clients: options.empty
        ? [{ ...CLIENTS[0], aum_krw: "0.00", holdings_count: 0 }]
        : CLIENTS,
    }),
  );

  await page.route("**/portfolio/holdings/**", async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204 });
      return;
    }
    await json(route, HOLDINGS[0]);
  });

  await page.route("**/portfolio/holdings**", async (route) => {
    const method = route.request().method();
    if (method === "POST") {
      await json(
        route,
        {
          ...HOLDINGS[0],
          id: 10,
          code: "KRW-ETH",
          client_id: "client-001",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        201,
      );
      return;
    }
    await json(route, options.empty ? [] : HOLDINGS);
  });

  await page.route("**/portfolio/summary**", (route) => {
    const url = new URL(route.request().url());
    json(route, summaryFor(url.searchParams.get("client_id") ?? "client-001", options.empty));
  });

  await page.route("**/portfolio/snapshots**", (route) =>
    json(
      route,
      Array.from({ length: 8 }, (_, index) => ({
        id: index + 1,
        user_id: "pb-demo",
        client_id: "client-001",
        client_name: "Client A",
        snapshot_date: `2026-04-${String(20 + index).padStart(2, "0")}`,
        total_value_krw: String(6000000 + index * 100000),
        total_pnl_krw: String(index * 100000),
        asset_class_breakdown: { stock_us: "0.21", crypto: "0.79" },
        holdings_detail: [],
        created_at: "2026-04-20T00:00:00Z",
      })),
    ),
  );

  await page.route("**/portfolio/sectors/heatmap**", (route) =>
    json(route, [{ sector: "Digital Assets", weight_pct: "79.00", pnl_pct: "11.76", intensity: "0.12" }]),
  );

  await page.route("**/portfolio/monthly-returns**", (route) =>
    json(route, [{ date: "2026-04-01", return_pct: "1.20", cell_level: 2 }]),
  );

  await page.route("**/portfolio/ai-insight**", (route) =>
    json(route, {
      summary: "Mock insight",
      bullets: ["Portfolio exposure is concentrated in crypto."],
      generated_at: "2026-04-30T00:00:00Z",
      stub_mode: true,
      gates: { schema: "pass", domain: "pass", critique: "pass" },
    }),
  );

  await page.route("**/portfolio/market-leaders**", (route) =>
    json(route, [
      {
        rank: 1,
        ticker: "AAPL",
        name: "Apple",
        market: "yahoo",
        price: "192.50",
        change_pct: "0.78",
        currency: "USD",
        logo_url: null,
        price_display: "$192.50",
        change_krw: null,
      },
    ]),
  );

  await page.route("**/portfolio/reports/client-briefing**", (route) =>
    json(route, {
      status: "success",
      client_context: { client_id: "client-001" },
      metrics: {},
      sections: [],
      evidence: [],
      gate_results: { schema: "pass", domain: "pass", critique: "pass" },
      export_ready: true,
      report_script: null,
    }),
  );
}

export async function mockMarketApis(page: Page) {
  await page.route("**/market/quotes/upbit/KRW-BTC**", (route) => json(route, BTC_QUOTE));
  await page.route("**/market/quotes/yahoo/AAPL**", (route) => json(route, AAPL_QUOTE));
  await page.route("**/market/quotes/**", (route) => json(route, AAPL_QUOTE));
  await page.route("**/market/ohlc/upbit/KRW-BTC**", (route) => json(route, ohlcFor(115000000)));
  await page.route("**/market/ohlc/yahoo/AAPL**", (route) => json(route, ohlcFor(188)));
  await page.route("**/market/ohlc/**", (route) => json(route, ohlcFor(188)));
  await page.route("**/market/symbol/**/indicators**", (route) => json(route, indicators()));
  await page.route("**/market/symbols/search**", (route) =>
    json(route, [
      { symbol: "AAPL", name: "Apple Inc.", asset_class: "stock", market: "yahoo", currency: "USD" },
      { symbol: "KRW-BTC", name: "Bitcoin", asset_class: "crypto", market: "upbit", currency: "KRW" },
      { symbol: "KRW-ETH", name: "Ethereum", asset_class: "crypto", market: "upbit", currency: "KRW" },
    ]),
  );
  await page.route("**/market/symbols**", (route) =>
    json(route, [{ symbol: "AAPL", name: "Apple Inc.", asset_class: "stock", market: "yahoo", currency: "USD" }]),
  );
  await page.route("**/search/news**", (route) =>
    json(route, [
      {
        doc_id: 1,
        chunk_id: 1,
        title: "Market update",
        source_url: "https://example.com/news",
        published_at: "2026-04-20T00:00:00Z",
        excerpt: "Fixture news item.",
        score: 0.9,
        thumbnail_url: null,
      },
    ]),
  );
}

export async function mockSettingsApis(page: Page) {
  const body = {
    display_name: "Demo User",
    name: "Demo User",
    email: "demo@example.com",
    language: "ko",
    timezone: "Asia/Seoul",
    notifications: {
      email_alerts: true,
      push_alerts: false,
      price_threshold_pct: 5,
      daily_digest: true,
    },
    theme: { mode: "system", accent: "violet" },
    data: {
      refresh_interval_sec: 30,
      auto_refresh: false,
      auto_backup: false,
      cache_size_mb: 128,
    },
    connected_accounts: {
      google: false,
      apple: false,
      kakao: false,
      github: true,
    },
    currency: "KRW",
    date_format: "YYYY-MM-DD",
    number_format: "ko-KR",
    auto_refresh: false,
    refresh_interval_sec: 30,
    market_data_source: "mock",
    risk_profile: "balanced",
    notifications_enabled: true,
    email_notifications: false,
    price_alerts_enabled: true,
    news_alerts_enabled: true,
    portfolio_alerts_enabled: true,
    created_at: "2026-04-01T00:00:00Z",
    updated_at: "2026-04-01T00:00:00Z",
  };
  await page.route("**/users/me/settings**", (route) => json(route, body));
}

export async function mockAnalyzeApis(page: Page) {
  await page.route("**/analyze**", (route) => {
    if (route.request().method() !== "POST") return route.continue();
    return json(route, {
      request_id: "mock-analysis",
      status: "ok",
      result: {
        asset_class: "stock",
        headline: "AAPL portfolio-aware analysis",
        narrative: "AAPL is held in the current portfolio.",
        summary: "AAPL analysis",
        highlights: ["Portfolio context included"],
        metrics: { latest_close: 192.5 },
        signals: [{ kind: "trend", strength: "medium", rationale: "fixture" }],
        evidence: [{ claim: "Fixture quote", source: "quote", rows: [0] }],
        confidence: 0.82,
      },
      meta: {
        asset_class: "stock",
        router_reason: "Fixture router reason",
        gates: { schema_gate: "pass", domain_gate: "pass", critique_gate: "pass" },
        latency_ms: 10,
        analyzer_name: "stock",
        evidence_snippets: ["Fixture quote"],
      },
    });
  });
}

export async function mockBaseApis(page: Page, options: { emptyPortfolio?: boolean } = {}) {
  await page.route("**/health", (route) =>
    json(route, { status: "ok", version: "test", services: { database: "ok", redis: "ok" } }),
  );
  await mockPortfolioApis(page, { empty: options.emptyPortfolio });
  await mockMarketApis(page);
  await mockSettingsApis(page);
  await mockAnalyzeApis(page);
  await page.route("**/ws/**", (route) => route.abort());
}

export async function submitCopilotQuery(page: Page, query: string) {
  const input = page.getByRole("textbox", { name: "copilot-input" });
  await expect(input).toBeVisible({ timeout: 10_000 });
  await input.fill(query);
  await expect(input).toHaveValue(query);
  await input.press("Enter");
  await expect(page.getByTestId("copilot-drawer")).toBeVisible({ timeout: 10_000 });
}

function sseEvent(payload: unknown) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

export async function mockCopilotSse(page: Page) {
  await page.route("**/copilot/query**", async (route) => {
    const raw = route.request().postData() ?? "{}";
    let query = "";
    try {
      query = String((JSON.parse(raw) as { query?: unknown }).query ?? "");
    } catch {
      query = raw;
    }
    const degraded = route.request().url().includes("mock_scenario=degraded") || /news|뉴스/i.test(query);
    const simulator = /30%|공시|filing|그 종목/i.test(query);
    const sessionId = "mock-session";
    const stepEvents = degraded
      ? [
          sseEvent({ type: "step.start", step_id: "comparison" }),
          sseEvent({
            type: "step.result",
            step_id: "comparison",
            card: {
              type: "news_rag_list",
              degraded: true,
              degraded_reason: "degraded fixture",
              items: [{ title: "AAPL recent news" }],
            },
          }),
          sseEvent({
            type: "step.gate",
            step_id: "comparison",
            gate: "domain",
            status: "fail",
            reason: "degraded fixture",
          }),
        ]
      : simulator
        ? [
            sseEvent({ type: "step.start", step_id: "comparison" }),
            sseEvent({
              type: "step.result",
              step_id: "comparison",
              card: {
                type: "comparison_table",
                symbols: ["AAPL", "TSLA", "NVDA"],
              },
            }),
            sseEvent({ type: "step.start", step_id: "simulator" }),
            sseEvent({
              type: "step.result",
              step_id: "simulator",
              card: {
                type: "simulator_result",
                symbols: ["AAPL", "NVDA"],
                shocked_value: 7000000,
              },
            }),
          ]
        : [
            sseEvent({ type: "step.start", step_id: "comparison" }),
            sseEvent({
              type: "step.result",
              step_id: "comparison",
              card: {
                type: "comparison_table",
                symbols: ["AAPL", "TSLA", "NVDA"],
              },
            }),
            sseEvent({ type: "step.start", step_id: "chart" }),
            sseEvent({ type: "step.result", step_id: "chart", card: { type: "chart", title: "AAPL TSLA NVDA chart" } }),
          ];

    const chunks = [
      sseEvent({
        type: "plan.ready",
        plan: {
          plan_id: "mock-plan",
          session_id: sessionId,
          steps: [
            { step_id: "comparison", agent: "comparison", inputs: {}, depends_on: [], gate_policy: { schema: true, domain: true, critique: true } },
            { step_id: "simulator", agent: "simulator", inputs: {}, depends_on: ["comparison"], gate_policy: { schema: true, domain: true, critique: true } },
            { step_id: "chart", agent: "portfolio", inputs: {}, depends_on: [], gate_policy: { schema: true, domain: true, critique: true } },
          ],
          created_at: "2026-04-20T00:00:00Z",
        },
      }),
      ...stepEvents,
      sseEvent({
        type: "final.card",
        card: {
          type: "text",
          body: simulator
            ? "요약: AAPL follow-up simulator result"
            : degraded
              ? "요약: AAPL degraded news summary"
              : "요약: AAPL TSLA NVDA summary",
        },
      }),
      sseEvent({ type: "done", session_id: sessionId, turn_id: `turn-${Date.now()}` }),
    ].join("");

    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
      },
      body: chunks,
    });
  });
}
