import { test, expect } from "@playwright/test";

test.describe("sprint-05 acceptance — follow-up 대화 UX", () => {
  test("두 번째 질의가 직전 질의의 종목을 유지", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Control+K");
    await page.getByRole("textbox", { name: /copilot|질의/i }).fill("AAPL 분석");
    await page.keyboard.press("Enter");
    await expect(page.getByText(/AAPL/)).toBeVisible({ timeout: 10_000 });

    await page.getByRole("textbox", { name: /copilot|질의/i }).fill("그 종목 공시 요약");
    await page.keyboard.press("Enter");
    await expect(page.getByText(/AAPL/).nth(1)).toBeVisible({ timeout: 15_000 });
  });
});
