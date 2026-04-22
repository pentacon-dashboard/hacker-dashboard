import { test, expect } from "@playwright/test";

test.describe("sprint-06 acceptance — copilot E2E 3종 headless pass", () => {
  test("3개 spec 파일이 존재", async () => {
    const fs = await import("node:fs");
    for (const name of [
      "frontend/e2e/copilot/single-turn.spec.ts",
      "frontend/e2e/copilot/follow-up.spec.ts",
      "frontend/e2e/copilot/degraded.spec.ts",
    ]) {
      expect(fs.existsSync(name)).toBe(true);
    }
  });

  test("mock 모드 degraded 배너가 뜬다", async ({ page }) => {
    await page.goto("/?copilot=1&mock_scenario=degraded");
    await page.getByRole("textbox", { name: "copilot-input" })
      .fill("AAPL 최근 뉴스");
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("copilot-degraded-card"))
      .toBeVisible({ timeout: 20_000 });
  });
});
