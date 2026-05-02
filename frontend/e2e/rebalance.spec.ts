import { test, expect, type Page } from "@playwright/test";

/**
 * 리밸런싱 제안 기능 E2E 테스트
 *
 * 모든 /portfolio/rebalance 호출은 page.route() 로 intercept — 실 LLM 호출 없이 동작.
 *
 * 시나리오:
 *   1. 기본 목표 비중으로 제안 받기 → 액션 테이블 렌더 (KRW-BTC Sell / AAPL Buy)
 *   2. 공격형 70/30 프리셋 선택 → 합계 100% 배지 확인
 *   3. 합계가 100% 아닐 때 "제안 받기" 버튼 비활성화
 *   4. degraded 상태 (llm_analysis=null) → "LLM 해석 실패" 배너 표시
 */

// ── Mock 데이터 ────────────────────────────────────────────────────────────────

const MOCK_REBALANCE_OK = {
  request_id: "test-xxx",
  status: "ok",
  current_allocation: {
    stock_kr: 0.07,
    stock_us: 0.19,
    crypto: 0.74,
    cash: 0,
    fx: 0,
  },
  target_allocation: {
    stock_kr: 0.2,
    stock_us: 0.4,
    crypto: 0.3,
    cash: 0.1,
    fx: 0,
  },
  drift: {
    stock_kr: -0.13,
    stock_us: -0.21,
    crypto: 0.44,
    cash: -0.1,
    fx: 0,
  },
  actions: [
    {
      action: "sell",
      market: "upbit",
      code: "KRW-BTC",
      asset_class: "crypto",
      quantity: "0.02",
      estimated_value_krw: "1700000",
      reason: "crypto 비중 축소",
    },
    {
      action: "buy",
      market: "yahoo",
      code: "AAPL",
      asset_class: "stock_us",
      quantity: "3",
      estimated_value_krw: "850000",
      reason: "stock_us 비중 보강",
    },
  ],
  expected_allocation: {
    stock_kr: 0.07,
    stock_us: 0.4,
    crypto: 0.3,
    cash: 0.23,
    fx: 0,
  },
  summary: {
    total_trades: 2,
    total_sell_value_krw: "1700000",
    total_buy_value_krw: "850000",
    rebalance_cost_estimate_krw: "6375",
  },
  llm_analysis: {
    headline: "코인 비중 축소, 미국주식 보강 권장",
    narrative:
      "crypto 비중이 74%로 집중도 리스크가 큽니다. 목표 30%로 축소하고 미국주식을 보강하는 리밸런싱을 권장합니다.",
    warnings: ["양도소득세 검토"],
    confidence: 0.82,
  },
  meta: {
    gates: {
      schema_gate: "pass",
      domain_gate: "pass",
      critique_gate: "pass",
    },
    evidence_snippets: [],
  },
};

const MOCK_REBALANCE_DEGRADED = {
  ...MOCK_REBALANCE_OK,
  status: "degraded",
  llm_analysis: null,
};

// ── Portfolio 페이지 mock 헬퍼 ─────────────────────────────────────────────────

async function mockPortfolioApis(page: Page) {
  await page.route("**/portfolio/clients**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "pb-demo",
        aum_krw: "15000000.00",
        client_count: 1,
        clients: [
          {
            client_id: "client-001",
            client_name: "Client A",
            aum_krw: "15000000.00",
            holdings_count: 1,
            risk_grade: "medium",
            risk_score_pct: "42.00",
            total_pnl_pct: "25.00",
          },
        ],
      }),
    });
  });

  // summary mock — holdings 있어야 리밸런싱 패널이 활성화됨
  await page.route("**/portfolio/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "pb-demo",
        client_id: "client-001",
        client_name: "Client A",
        total_value_krw: "15000000.00",
        total_cost_krw: "12000000.00",
        total_pnl_krw: "3000000.00",
        total_pnl_pct: "25.00",
        daily_change_krw: "150000.00",
        daily_change_pct: "1.00",
        asset_class_breakdown: {
          stock_kr: 0.07,
          stock_us: 0.19,
          crypto: 0.74,
          cash: 0,
          fx: 0,
        },
        holdings: [
          {
            id: 1,
            user_id: "pb-demo",
            client_id: "client-001",
            market: "upbit",
            code: "KRW-BTC",
            quantity: "0.05",
            avg_cost: "85000000",
            currency: "KRW",
            current_price_krw: "95000000",
            value_krw: "4750000",
            pnl_krw: "500000",
            pnl_pct: "11.76",
            asset_class: "crypto",
            created_at: "2026-04-01T00:00:00Z",
            updated_at: "2026-04-19T00:00:00Z",
          },
        ],
      }),
    });
  });

  // snapshots mock
  await page.route("**/portfolio/snapshots*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/portfolio/sectors/heatmap**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          sector: "Digital Assets",
          weight_pct: "74.00",
          pnl_pct: "11.76",
          intensity: "0.12",
        },
      ]),
    });
  });

  await page.route("**/portfolio/monthly-returns**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { date: "2026-04-01", return_pct: "1.20", cell_level: 2 },
      ]),
    });
  });

  await page.route("**/portfolio/ai-insight**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: "Mock insight",
        bullets: ["Mock bullet"],
        generated_at: "2026-04-30T00:00:00Z",
        stub_mode: true,
        gates: { schema: "pass", domain: "pass", critique: "pass" },
      }),
    });
  });
}

// ── 테스트 ─────────────────────────────────────────────────────────────────────

test.describe("Rebalance proposal", () => {
  test("기본 목표 비중으로 제안 받기 → 액션 테이블 렌더", async ({ page }) => {
    await mockPortfolioApis(page);

    await page.route("**/portfolio/rebalance", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_REBALANCE_OK),
      });
    });

    await page.goto("/clients/client-001");

    // "제안 받기" 버튼 클릭
    const submitBtn = page.getByRole("button", { name: /제안 받기/ });
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 액션 테이블에 종목 코드 확인
    const actionTable = page.getByTestId("rebalance-action-table");
    await expect(actionTable.getByText(/upbit \/ KRW-BTC/)).toBeVisible();
    await expect(actionTable.getByText(/yahoo \/ AAPL/)).toBeVisible();

    // LLM 해석 헤드라인 확인
    await expect(page.getByText(/코인 비중 축소/)).toBeVisible();
  });

  test("공격형 70/30 프리셋 선택 → 합계 100% 배지 확인", async ({ page }) => {
    await mockPortfolioApis(page);

    // rebalance 요청은 발생하지 않지만 route 등록해두어 오류 방지
    await page.route("**/portfolio/rebalance", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_REBALANCE_OK),
      });
    });

    await page.goto("/clients/client-001");

    // 공격형 프리셋 버튼 클릭
    await page.getByRole("button", { name: /공격형/ }).click();

    // 합계 100.0% 배지 확인
    await expect(page.getByText(/100\.0%/).first()).toBeVisible();
  });

  test("합계 100% 미만이면 제안 받기 비활성화", async ({ page }) => {
    await mockPortfolioApis(page);

    await page.route("**/portfolio/rebalance", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_REBALANCE_OK),
      });
    });

    await page.goto("/clients/client-001");

    // 안정형 프리셋(합계 100%)을 먼저 선택해 기준선을 맞춘 뒤
    // 슬라이더 중 하나를 JS로 조작해 합계를 100이 아니게 만든다.
    // (shadcn Slider는 aria-valuenow로 현재 값 노출)
    // 여기서는 로컬스토리지를 직접 조작해 합이 90인 상태로 시작.
    await page.evaluate(() => {
      localStorage.setItem(
        "hd.rebalanceTarget",
        JSON.stringify({ stock_kr: 10, stock_us: 20, crypto: 30, cash: 30 }),
      );
    });
    await page.reload();

    // aria-disabled 또는 disabled 속성 확인
    const submitBtn = page.getByRole("button", { name: /제안 받기/ });
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toBeDisabled();
  });

  test("degraded 상태 → LLM 해석 실패 배너 표시", async ({ page }) => {
    await mockPortfolioApis(page);

    // degraded 응답으로 재등록
    await page.route("**/portfolio/rebalance", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_REBALANCE_DEGRADED),
      });
    });

    await page.goto("/clients/client-001");

    const submitBtn = page.getByRole("button", { name: /제안 받기/ });
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // "LLM 해석 실패" 배너 표시 확인
    await expect(
      page.getByRole("heading", { name: "LLM 해석 실패" }),
    ).toBeVisible();
  });
});
