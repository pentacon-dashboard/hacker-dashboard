import { test, expect, type Page } from "@playwright/test";

const CLIENTS_RESPONSE = {
  user_id: "pb-demo",
  aum_krw: "135000000.00",
  client_count: 2,
  clients: [
    {
      client_id: "client-001",
      client_name: "고객 A",
      aum_krw: "90000000.00",
      holdings_count: 3,
      risk_grade: "medium",
      risk_score_pct: "42.00",
      total_pnl_pct: "12.50",
    },
    {
      client_id: "client-002",
      client_name: "고객 B",
      aum_krw: "45000000.00",
      holdings_count: 2,
      risk_grade: "low",
      risk_score_pct: "18.00",
      total_pnl_pct: "-1.40",
    },
  ],
};

const BASE_HOLDINGS = [
  {
    id: 1,
    market: "yahoo",
    code: "AAPL",
    quantity: "10.00000000",
    avg_cost: "180.0000",
    currency: "USD",
    current_price: "212.8000",
    current_price_krw: "289500.00",
    value_krw: "2895000.00",
    cost_krw: "2450000.00",
    pnl_krw: "445000.00",
    pnl_pct: "18.16",
  },
  {
    id: 2,
    market: "naver_kr",
    code: "005930.KS",
    quantity: "30.00000000",
    avg_cost: "71000.0000",
    currency: "KRW",
    current_price: "74200.0000",
    current_price_krw: "74200.00",
    value_krw: "2226000.00",
    cost_krw: "2130000.00",
    pnl_krw: "96000.00",
    pnl_pct: "4.51",
  },
  {
    id: 3,
    market: "upbit",
    code: "KRW-BTC",
    quantity: "0.05000000",
    avg_cost: "66000000.0000",
    currency: "KRW",
    current_price: "73400000.0000",
    current_price_krw: "73400000.00",
    value_krw: "3670000.00",
    cost_krw: "3300000.00",
    pnl_krw: "370000.00",
    pnl_pct: "11.21",
  },
];

function summaryFor(clientId: string) {
  const isClientB = clientId === "client-002";
  return {
    user_id: "pb-demo",
    client_id: clientId,
    client_name: isClientB ? "고객 B" : "고객 A",
    total_value_krw: isClientB ? "45000000.00" : "90000000.00",
    total_cost_krw: isClientB ? "45630000.00" : "80000000.00",
    total_pnl_krw: isClientB ? "-630000.00" : "10000000.00",
    total_pnl_pct: isClientB ? "-1.40" : "12.50",
    daily_change_krw: isClientB ? "-82000.00" : "373088.00",
    daily_change_pct: isClientB ? "-0.18" : "0.41",
    asset_class_breakdown: isClientB
      ? { stock_kr: "0.45", stock_us: "0.35", cash: "0.20" }
      : { stock_us: "0.45", stock_kr: "0.30", crypto: "0.25" },
    holdings: isClientB ? BASE_HOLDINGS.slice(0, 2) : BASE_HOLDINGS,
    holdings_count: isClientB ? 2 : 3,
    worst_asset_pct: isClientB ? "-1.40" : "4.51",
    risk_score_pct: isClientB ? "18.00" : "42.00",
    period_change_pct: isClientB ? "-0.90" : "3.20",
    period_days: 30,
    dimension_breakdown: isClientB
      ? [
          { label: "stock_kr", weight_pct: "45.00", pnl_pct: "-1.00" },
          { label: "stock_us", weight_pct: "35.00", pnl_pct: "0.60" },
          { label: "cash", weight_pct: "20.00", pnl_pct: "0.00" },
        ]
      : [
          { label: "stock_us", weight_pct: "45.00", pnl_pct: "12.00" },
          { label: "stock_kr", weight_pct: "30.00", pnl_pct: "4.50" },
          { label: "crypto", weight_pct: "25.00", pnl_pct: "11.20" },
        ],
  };
}

async function setupHomeRoutes(page: Page, summaryClientIds: string[] = []) {
  await page.route("**/portfolio/clients**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(CLIENTS_RESPONSE),
    });
  });

  await page.route("**/portfolio/summary**", async (route) => {
    const url = new URL(route.request().url());
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    summaryClientIds.push(clientId);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(summaryFor(clientId)),
    });
  });

  await page.route("**/portfolio/snapshots**", async (route) => {
    const url = new URL(route.request().url());
    const clientId = url.searchParams.get("client_id") ?? "client-001";
    const base = clientId === "client-002" ? 45_000_000 : 90_000_000;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        Array.from({ length: 8 }, (_, index) => ({
          id: index + 1,
          user_id: "pb-demo",
          client_id: clientId,
          client_name: clientId === "client-002" ? "고객 B" : "고객 A",
          snapshot_date: `2026-04-${String(20 + index).padStart(2, "0")}`,
          total_value_krw: String(base + index * 120_000),
          total_pnl_krw: String(index * 120_000),
          asset_class_breakdown: summaryFor(clientId).asset_class_breakdown,
          holdings_detail: [],
          created_at: "2026-04-20T00:00:00Z",
        })),
      ),
    });
  });

  await page.route("**/portfolio/sectors/heatmap**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { sector: "Tech", weight_pct: "45.00", pnl_pct: "2.10", intensity: "0.21" },
      ]),
    });
  });

  await page.route("**/portfolio/monthly-returns**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ date: "2026-04-01", return_pct: "1.20", cell_level: 2 }]),
    });
  });

  await page.route("**/portfolio/ai-insight**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: "고객 포트폴리오 인사이트",
        bullets: ["선택 고객 기준으로 데이터를 표시합니다."],
        generated_at: "2026-04-30T00:00:00Z",
        stub_mode: true,
        gates: { schema: "pass", domain: "pass", critique: "pass" },
      }),
    });
  });

  await page.route("**/portfolio/market-leaders**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          rank: 1,
          ticker: "NVDA",
          name: "NVIDIA",
          market: "yahoo",
          price: "512.40",
          change_pct: "3.12",
          currency: "USD",
          logo_url: null,
          price_display: "$512.40",
          change_krw: "+4,420",
        },
      ]),
    });
  });

  await page.route("**/search/news**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          doc_id: 101,
          chunk_id: 1,
          source_url: "https://example.com/news",
          title: "선택 고객 보유종목 관련 뉴스",
          published_at: "2026-04-30T00:00:00Z",
          excerpt: "대시보드 뉴스 패널 테스트 기사입니다.",
          score: 0.9,
          thumbnail_url: null,
        },
      ]),
    });
  });
}

test("home renders the unified PB client book and dashboard", async ({ page }) => {
  await setupHomeRoutes(page);
  await page.goto("/");

  await expect(page.locator("[data-testid='client-dashboard-home']")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.locator("[data-testid='client-book-total-aum']")).toBeVisible();
  await expect(page.locator("[data-testid='client-card-client-001']")).toBeVisible();
  await expect(page.locator("[data-testid='client-card-client-002']")).toBeVisible();
  await expect(page.locator("[data-testid='dashboard-home']")).toBeVisible();
  await expect(page.locator("[data-testid='client-book-table']")).toContainText("고객 B");
});

test("selecting a client changes dashboard data without leaving home", async ({ page }) => {
  const summaryClientIds: string[] = [];
  await setupHomeRoutes(page, summaryClientIds);
  await page.goto("/");

  await page.locator("[data-testid='client-select-client-002']").click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("[data-testid='dashboard-home']")).toContainText(
    "고객 B 고객 포트폴리오 대시보드",
  );
  await expect(page.locator("[data-testid='selected-client-workspace-link']")).toHaveAttribute(
    "href",
    "/clients/client-002",
  );
  await expect
    .poll(() => summaryClientIds.includes("client-002"))
    .toBeTruthy();
});

test("workspace link opens selected client detail and back returns home", async ({ page }) => {
  await setupHomeRoutes(page);
  await page.goto("/");

  await page.locator("[data-testid='client-select-client-002']").click();
  await page.locator("[data-testid='client-workspace-link-client-002']").click();

  await expect(page).toHaveURL(/\/clients\/client-002$/);
  await expect(page.locator("[data-testid='client-workspace']")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.locator("h1")).toContainText("고객 B 워크스페이스");

  await page.locator("[data-testid='client-workspace-back']").click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("[data-testid='client-dashboard-home']")).toBeVisible();
});

test("/dashboard redirects to the unified home", async ({ page }) => {
  await setupHomeRoutes(page);
  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("[data-testid='client-dashboard-home']")).toBeVisible({
    timeout: 10_000,
  });
});
