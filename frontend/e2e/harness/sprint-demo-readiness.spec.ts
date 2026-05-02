import { test, expect } from "@playwright/test";
import { mockBaseApis } from "../fixtures/api";

test("demo sidebar shows demo identity", async ({ page }) => {
  await mockBaseApis(page);
  await page.goto("/");
  await expect(page.locator("body")).toContainText(/Demo\s*User|demo@demo\.com/i, {
    timeout: 10_000,
  });
});

test("demo dashboard shows client KPIs, market leaders, and news", async ({ page }) => {
  await mockBaseApis(page);
  await page.goto("/");
  await expect(page.getByTestId("client-dashboard-home")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByTestId("kpi-total-value")).toBeVisible();
  await expect(page.getByTestId("section-top-holdings")).toBeVisible();
  await expect(page.getByTestId("client-monitoring-signals")).toBeVisible();
});

test("demo symbol detail shows RSI and MACD subcharts", async ({ page }) => {
  await mockBaseApis(page);
  await page.goto("/symbol/yahoo/AAPL");
  await expect(page.locator("body")).toContainText(/RSI/i, { timeout: 15_000 });
  await expect(page.locator("body")).toContainText(/MACD/i);
});

test("demo copilot page renders", async ({ page }) => {
  await mockBaseApis(page);
  await page.goto("/copilot");
  await expect(page.locator("body")).toContainText(/Copilot|코파일럿/i, {
    timeout: 10_000,
  });
});

test("Vercel production health is reachable when configured", async ({ request }) => {
  const url = process.env.VERCEL_URL ?? process.env.PRODUCTION_URL;
  test.skip(!url, "VERCEL_URL is not configured for local demo readiness");
  const response = await request.get(`${url}/api/health`);
  expect(response.status()).toBeLessThan(500);
});
