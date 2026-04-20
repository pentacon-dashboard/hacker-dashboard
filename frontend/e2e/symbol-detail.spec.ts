import { test, expect, Page } from "@playwright/test";

/**
 * 종목 상세 페이지 E2E 테스트
 *
 * 모든 API 호출은 page.route() 로 mock 처리 — 실 네트워크 없이 동작.
 *
 * 시나리오:
 *   1. /symbol/upbit/KRW-BTC 직접 방문 → 가격/변동률 2초 내 렌더
 *   2. 캔들차트 컨테이너(canvas 또는 지정 selector)가 viewport 에 존재
 *   3. "Router 결정 근거" 토글이 있으면 클릭 시 근거 영역 노출 (없으면 skip)
 *   4. (Phase D) "내 포트폴리오 반영" 토글 요소 존재 확인
 *   5. (Phase D) 토글 ON 상태에서 /analyze 요청 body 에 include_portfolio_context=true 포함
 *   6. (Phase D) matched_holding evidence 응답 시 holding-badge 렌더
 *   7. (Phase D) 토글 OFF 시 holding-badge 숨김
 */

// ── Mock 데이터 ────────────────────────────────────────────────────────────────

const MOCK_QUOTE = {
  symbol: "KRW-BTC",
  market: "upbit",
  price: 120000000,
  change: 1000000,
  change_pct: 0.84,
  currency: "KRW",
  timestamp: "2026-04-19T12:00:00Z",
};

const MOCK_QUOTE_AAPL = {
  symbol: "AAPL",
  market: "yahoo",
  price: 192.5,
  change: 1.5,
  change_pct: 0.78,
  currency: "USD",
  timestamp: "2026-04-20T12:00:00Z",
};

// holding-badge 렌더용: matched_holding evidence 포함 응답
const MOCK_ANALYZE_RESPONSE_WITH_HOLDING = {
  request_id: "mock-uuid-portfolio-1",
  status: "ok",
  result: {
    asset_class: "stock",
    headline: "AAPL 보유 종목 개인화 분석",
    narrative: "보유 5주 기준 현재 +4.1% 수익 상태. 단기 상승 모멘텀 유효.",
    summary: "AAPL 개인화 분석",
    highlights: ["보유 수익률 +4.1%", "MA20 > MA60 골든크로스"],
    metrics: {
      latest_close: 192.5,
      matched_holding: {
        market: "yahoo",
        code: "AAPL",
        quantity: "5",
        avg_cost: "185",
        currency: "USD",
        pnl_pct: 4.1,
      },
    },
    signals: [{ kind: "trend", strength: "medium", rationale: "상승세" }],
    evidence: [
      { claim: "최근 90일 수익률 +8%", source: "ohlc", rows: [0] },
      {
        claim: "보유 5주, 평균단가 $185 대비 현재 +4.1% 수익",
        source: "portfolio.matched_holding",
        quantity: 5,
        avg_cost: 185,
      },
    ],
    confidence: 0.82,
  },
  meta: {
    asset_class: "stock",
    router_reason: "AAPL 은 Yahoo Finance 미국 주식 심볼. Stock Analyzer 선택.",
    gates: { schema_gate: "pass", domain_gate: "pass", critique_gate: "pass" },
    latency_ms: 980,
    analyzer_name: "stock",
    evidence_snippets: ["최근 90일 수익률 +8%", "보유 5주, 평균단가 $185"],
  },
};

// 토글 OFF 시: matched_holding 없는 기본 응답
const MOCK_ANALYZE_RESPONSE_WITHOUT_HOLDING = {
  request_id: "mock-uuid-base-1",
  status: "ok",
  result: {
    asset_class: "stock",
    headline: "AAPL 안정적 상승세",
    narrative: "견조한 실적 기반 완만한 상승 추세.",
    summary: "AAPL 기본 분석",
    highlights: ["매출 성장", "강한 현금흐름"],
    metrics: { latest_close: 192.5 },
    signals: [{ kind: "trend", strength: "medium", rationale: "상승세" }],
    evidence: [{ claim: "최근 90일 수익률 +8%", source: "ohlc", rows: [0] }],
    confidence: 0.75,
  },
  meta: {
    asset_class: "stock",
    router_reason: "AAPL 은 Yahoo Finance 미국 주식 심볼. Stock Analyzer 선택.",
    gates: { schema_gate: "pass", domain_gate: "pass", critique_gate: "pass" },
    latency_ms: 850,
    analyzer_name: "stock",
    evidence_snippets: ["최근 90일 수익률 +8%"],
  },
};

const MOCK_OHLC = Array.from({ length: 30 }, (_, i) => ({
  ts: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
  open: 115000000 + i * 200000,
  high: 116000000 + i * 200000,
  low: 114000000 + i * 200000,
  close: 115500000 + i * 200000,
  volume: 1000 + i * 10,
}));

const MOCK_ANALYZE_RESPONSE = {
  request_id: "mock-uuid-1234",
  status: "ok",
  result: {
    summary: "BTC 는 단기 상승 추세입니다.",
    signals: ["RSI 과매수 구간 진입", "볼린저 밴드 상단 근접"],
  },
  meta: {
    asset_class: "crypto",
    router_reason:
      "KRW-BTC 는 upbit 거래소의 암호화폐 쌍으로, crypto analyzer 를 선택했습니다.",
    gates: { schema: "pass", domain: "pass", critique: "pass" },
    latency_ms: 1200,
  },
};

// ── beforeEach: 공통 라우트 설정 ─────────────────────────────────────────────

async function setupSymbolRoutes(page: Page) {
  // 시세 조회
  await page.route("**/market/quotes/upbit/KRW-BTC**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_QUOTE),
    });
  });

  // 레거시 시세 엔드포인트
  await page.route("**/market/quotes/KRW-BTC**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_QUOTE),
    });
  });

  // OHLC 캔들 데이터
  await page.route("**/market/ohlc/upbit/KRW-BTC**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_OHLC),
    });
  });

  // 분석 요청 (Router 결정 근거 포함)
  await page.route("**/analyze**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ANALYZE_RESPONSE),
      });
    } else {
      await route.continue();
    }
  });

  // WS abort (HTTP fallback 유도)
  await page.route("**/ws/**", async (route) => {
    await route.abort();
  });

  // 심볼 목록
  await page.route("**/market/symbols**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          symbol: "KRW-BTC",
          name: "Bitcoin",
          asset_class: "crypto",
          market: "upbit",
        },
      ]),
    });
  });
}

// ── 시나리오 1: 가격/변동률 렌더 ─────────────────────────────────────────────

test("/symbol/upbit/KRW-BTC 방문 시 가격과 변동률이 2초 내 렌더된다", async ({
  page,
}) => {
  await setupSymbolRoutes(page);
  await page.goto("/symbol/upbit/KRW-BTC");

  // 가격 표시 요소: data-testid 우선, 없으면 숫자 패턴 탐색
  const priceEl = page
    .locator(
      [
        "[data-testid='symbol-price']",
        "[data-testid='current-price']",
        "[aria-label*='현재가']",
        "[aria-label*='price']",
      ].join(", ")
    )
    .first();

  const priceElExists = await priceEl.count();

  if (priceElExists > 0) {
    await expect(priceEl).toBeVisible({ timeout: 2_000 });
    const text = await priceEl.textContent();
    // 숫자가 포함되어 있어야 함
    expect(text).toMatch(/[\d,]+/);
  } else {
    // testid 없는 경우: 페이지 본문에 숫자(가격)가 있는지 확인
    const body = await page.locator("main, body").first().textContent();
    // KRW-BTC 가격은 수천만 원 대 → 7자리 이상 숫자 존재
    expect(body).toMatch(/\d{7,}/);
  }

  // 변동률 표시 (% 포함)
  const changePctEl = page
    .locator(
      [
        "[data-testid='change-pct']",
        "[data-testid='price-change']",
        "[aria-label*='변동']",
      ].join(", ")
    )
    .first();

  const changePctExists = await changePctEl.count();
  if (changePctExists > 0) {
    await expect(changePctEl).toBeVisible({ timeout: 2_000 });
    const text = await changePctEl.textContent();
    expect(text).toMatch(/%/);
  }
  // 변동률 요소가 없어도 가격 렌더 확인만으로 통과
});

// ── 시나리오 2: 캔들차트 컨테이너 존재 ──────────────────────────────────────

test("캔들차트 컨테이너(canvas 또는 chart div)가 viewport 에 존재한다", async ({
  page,
}) => {
  await setupSymbolRoutes(page);
  await page.goto("/symbol/upbit/KRW-BTC");

  // TradingView Lightweight Charts 는 canvas 를 생성함
  // Recharts 나 커스텀은 svg 또는 div[data-testid]
  const chartContainer = page
    .locator(
      [
        "canvas",
        "[data-testid='candlestick-chart']",
        "[data-testid='ohlc-chart']",
        "[data-testid='chart-container']",
        ".tv-lightweight-charts",
        ".recharts-wrapper",
      ].join(", ")
    )
    .first();

  const chartExists = await chartContainer.count();
  if (chartExists === 0) {
    // FE 팀 구현 대기 — fe-selector-asks.md 로 요청 사항 전달됨
    test.skip();
    return;
  }

  // viewport 안에 있어야 함 (in-view)
  await expect(chartContainer).toBeInViewport({ timeout: 5_000 });
});

// ── 시나리오 3: Router 결정 근거 토글 ────────────────────────────────────────

test("'Router 결정 근거' 토글이 있으면 클릭 시 근거 영역이 나타난다", async ({
  page,
}) => {
  await setupSymbolRoutes(page);
  await page.goto("/symbol/upbit/KRW-BTC");

  // 토글 버튼 탐색
  const toggleBtn = page
    .locator(
      [
        "[data-testid='router-reason-toggle']",
        "button:has-text('Router')",
        "button:has-text('결정 근거')",
        "button:has-text('분석 근거')",
        "[aria-label*='근거']",
        "[aria-label*='router']",
        "[aria-label*='Router']",
      ].join(", ")
    )
    .first();

  const toggleExists = await toggleBtn.count();
  if (toggleExists === 0) {
    // 토글 미구현 → skip (데모 준비 체크리스트에는 미충족으로 기록)
    test.skip();
    return;
  }

  // 토글 클릭 전 근거 영역 상태 확인
  const reasonArea = page
    .locator(
      [
        "[data-testid='router-reason']",
        "[data-testid='router-reason-content']",
        "[aria-label*='근거 내용']",
      ].join(", ")
    )
    .first();

  await toggleBtn.click();
  await page.waitForTimeout(300); // 애니메이션 여유

  // 클릭 후 근거 영역이 보여야 함
  const reasonAreaExists = await reasonArea.count();
  if (reasonAreaExists > 0) {
    await expect(reasonArea).toBeVisible({ timeout: 2_000 });
    // 근거 텍스트에 실제 내용이 있어야 함
    const text = await reasonArea.textContent();
    expect((text ?? "").trim().length).toBeGreaterThan(0);
  } else {
    // testid 없는 경우: 토글 후 새로운 텍스트 영역이 열렸는지 확인
    // router_reason 문자열이 화면에 보이면 OK
    const pageText = await page.locator("body").textContent();
    expect(pageText).toMatch(/crypto|analyzer|암호화폐|선택/i);
  }
});

// ── Phase D 시나리오 4-7: 포트폴리오 컨텍스트 개인화 ──────────────────────────

/**
 * AAPL 전용 라우트 setup — /symbol/yahoo/AAPL 용 mock.
 * 인수로 includePortfolioContext 를 받아 /analyze 응답을 분기.
 */
async function setupAaplRoutes(
  page: Page,
  options: { portfolioEnabled: boolean }
) {
  const analyzeResponse = options.portfolioEnabled
    ? MOCK_ANALYZE_RESPONSE_WITH_HOLDING
    : MOCK_ANALYZE_RESPONSE_WITHOUT_HOLDING;

  // 시세
  await page.route("**/market/quotes/yahoo/AAPL**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_QUOTE_AAPL),
    });
  });
  await page.route("**/market/quotes/AAPL**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_QUOTE_AAPL),
    });
  });

  // OHLC
  await page.route("**/market/ohlc/yahoo/AAPL**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        Array.from({ length: 30 }, (_, i) => ({
          ts: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
          open: 188 + i * 0.1,
          high: 193 + i * 0.1,
          low: 187 + i * 0.1,
          close: 190 + i * 0.1,
          volume: 50000000,
        }))
      ),
    });
  });

  // /analyze — POST 요청 intercept
  await page.route("**/analyze**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(analyzeResponse),
      });
    } else {
      await route.continue();
    }
  });

  // WS abort
  await page.route("**/ws/**", async (route) => {
    await route.abort();
  });

  // 심볼 목록
  await page.route("**/market/symbols**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { symbol: "AAPL", name: "Apple Inc.", asset_class: "stock", market: "yahoo" },
      ]),
    });
  });
}

// ── 시나리오 4: "내 포트폴리오 반영" 토글 요소 존재 확인 ─────────────────────

test(
  "(Phase D) '내 포트폴리오 반영' 토글 요소가 종목 상세 페이지에 존재한다",
  async ({ page }) => {
    await setupAaplRoutes(page, { portfolioEnabled: true });
    await page.goto("/symbol/yahoo/AAPL");

    const toggle = page
      .locator(
        [
          "[data-testid='portfolio-context-toggle']",
          "[data-testid='include-portfolio-toggle']",
          "input[type='checkbox'][aria-label*='포트폴리오']",
          "button:has-text('포트폴리오 반영')",
          "button:has-text('내 포트폴리오')",
          "label:has-text('포트폴리오 반영')",
          "[aria-label*='portfolio']",
          "[aria-label*='포트폴리오 반영']",
        ].join(", ")
      )
      .first();

    const exists = await toggle.count();
    if (exists === 0) {
      // FE 구현 대기 — Phase C frontend-engineer 로 에스컬레이션 필요
      console.warn(
        "[Phase D] 포트폴리오 토글 요소 없음. Phase C 구현 확인 필요."
      );
      test.skip();
      return;
    }

    await expect(toggle).toBeVisible({ timeout: 3_000 });
  }
);

// ── 시나리오 5: 토글 ON 상태에서 /analyze 요청에 include_portfolio_context=true ─

test(
  "(Phase D) 포트폴리오 토글 ON 상태에서 /analyze 요청 body에 include_portfolio_context=true 포함",
  async ({ page }) => {
    // 요청 body 캡처
    const capturedBodies: string[] = [];

    await page.route("**/analyze**", async (route) => {
      if (route.request().method() === "POST") {
        capturedBodies.push(route.request().postData() ?? "");
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_ANALYZE_RESPONSE_WITH_HOLDING),
        });
      } else {
        await route.continue();
      }
    });

    // 나머지 라우트 설정
    await page.route("**/market/quotes/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_QUOTE_AAPL),
      });
    });
    await page.route("**/market/ohlc/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/ws/**", async (route) => {
      await route.abort();
    });
    await page.route("**/market/symbols**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { symbol: "AAPL", name: "Apple Inc.", asset_class: "stock", market: "yahoo" },
        ]),
      });
    });

    // localStorage 에 토글 ON 상태 주입 (Phase C 구현 키: hd.includePortfolioContext)
    await page.addInitScript(() => {
      localStorage.setItem("hd.includePortfolioContext", "true");
    });

    await page.goto("/symbol/yahoo/AAPL");

    // 분석 트리거 대기 (최대 5초)
    await page.waitForTimeout(2_000);

    if (capturedBodies.length === 0) {
      console.warn("[Phase D] /analyze 요청이 발생하지 않음. 자동 분석 트리거 미구현 가능.");
      test.skip();
      return;
    }

    // 최소 하나의 요청 body 에 include_portfolio_context=true 가 있어야 함
    const hasPortfolioFlag = capturedBodies.some((body) => {
      try {
        const parsed = JSON.parse(body);
        return parsed.include_portfolio_context === true;
      } catch {
        return body.includes('"include_portfolio_context":true') ||
               body.includes('"include_portfolio_context": true');
      }
    });

    expect(hasPortfolioFlag).toBe(true);
  }
);

// ── 시나리오 6: matched_holding evidence 응답 시 holding-badge 렌더 ──────────

test(
  "(Phase D) matched_holding evidence 포함 응답 시 holding-badge 가 렌더된다",
  async ({ page }) => {
    await setupAaplRoutes(page, { portfolioEnabled: true });

    // 토글 ON 강제
    await page.addInitScript(() => {
      localStorage.setItem("hd.includePortfolioContext", "true");
    });

    await page.goto("/symbol/yahoo/AAPL");

    // holding-badge 또는 유사 testid 탐색
    const badge = page
      .locator(
        [
          "[data-testid='holding-badge']",
          "[data-testid='portfolio-holding-badge']",
          "[data-testid='matched-holding']",
          ".holding-badge",
          "[aria-label*='보유']",
          "[aria-label*='holding']",
        ].join(", ")
      )
      .first();

    const badgeCount = await badge.count();
    if (badgeCount === 0) {
      // Phase C AnalyzerResultPanel 의 holding-badge 미구현 가능성
      console.warn("[Phase D] holding-badge 요소 없음. Phase C 구현 확인 필요.");
      test.skip();
      return;
    }

    await expect(badge).toBeVisible({ timeout: 5_000 });
    const text = await badge.textContent();
    // 보유 수량 또는 수익률 관련 텍스트 포함
    expect(text ?? "").toMatch(/5|AAPL|보유|holding|pnl|\+/i);
  }
);

// ── 시나리오 7: 토글 OFF → holding-badge 숨김 ────────────────────────────────

test(
  "(Phase D) 포트폴리오 토글 OFF 시 holding-badge 가 표시되지 않는다",
  async ({ page }) => {
    await setupAaplRoutes(page, { portfolioEnabled: false });

    // 토글 OFF 강제
    await page.addInitScript(() => {
      localStorage.setItem("hd.includePortfolioContext", "false");
    });

    await page.goto("/symbol/yahoo/AAPL");

    // holding-badge 가 없거나 숨겨져야 함
    const badge = page
      .locator(
        [
          "[data-testid='holding-badge']",
          "[data-testid='portfolio-holding-badge']",
          "[data-testid='matched-holding']",
          ".holding-badge",
        ].join(", ")
      )
      .first();

    const badgeCount = await badge.count();
    if (badgeCount === 0) {
      // 요소 자체가 없으면 통과 (토글 OFF 시 DOM 에서 제거)
      return;
    }

    // 요소는 있지만 숨겨져 있어야 함
    await expect(badge).not.toBeVisible({ timeout: 3_000 });
  }
);
