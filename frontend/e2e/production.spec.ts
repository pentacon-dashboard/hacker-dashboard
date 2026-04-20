import { test, expect } from "@playwright/test";

/**
 * 프로덕션 스모크 테스트
 *
 * PROD_URL 환경변수로 배포 URL 지정.
 * API mock 없이 실제 BE 에 연결하여 기본 렌더만 검증.
 *
 * 실행 방법:
 *   PROD_URL=https://hacker-dashboard.vercel.app npx playwright test e2e/production.spec.ts
 */

const PROD_URL = process.env.PROD_URL ?? "http://localhost:3000";
const BE_URL = process.env.BE_URL ?? "https://hacker-dashboard-api.fly.dev";

test.use({ baseURL: PROD_URL });

// ── 시나리오 1: BE /health ──────────────────────────────────────────────────
test("BE /health 가 200 을 반환한다", async ({ request }) => {
  const res = await request.get(`${BE_URL}/health`);
  expect(res.status()).toBe(200);

  const body = await res.json();
  expect(body).toHaveProperty("status");
  expect(body.status).toMatch(/ok|healthy/i);
});

// ── 시나리오 2: 홈(/) 렌더 ─────────────────────────────────────────────────
test("홈 페이지가 렌더되고 주요 영역이 보인다", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle", timeout: 30_000 });

  // 페이지 타이틀 존재
  const title = await page.title();
  expect(title.length).toBeGreaterThan(0);

  // main 영역 가시성
  const main = page.locator("main, [role='main'], [id='main-content']").first();
  await expect(main).toBeVisible({ timeout: 15_000 });
});

// ── 시나리오 3: /watchlist 렌더 ────────────────────────────────────────────
test("/watchlist 페이지가 렌더된다", async ({ page }) => {
  await page.goto("/watchlist", { waitUntil: "domcontentloaded", timeout: 30_000 });

  // 에러 페이지가 아닌지 확인
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toMatch(/500|Internal Server Error/i);

  // heading 또는 list 존재 여부 (느슨한 검증)
  const hasContent = await page
    .locator("h1, h2, [role='list'], table, [data-testid]")
    .count();
  expect(hasContent).toBeGreaterThan(0);
});
