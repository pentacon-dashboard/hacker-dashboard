import { test, expect } from "@playwright/test";
import path from "node:path";
import { mockBaseApis, mockCopilotSse, submitCopilotQuery } from "../fixtures/api";

test.describe("sprint-06 acceptance — copilot E2E 3종 headless pass", () => {
  test("3개 spec 파일이 존재", async () => {
    const fs = await import("node:fs");
    for (const name of [
      "frontend/e2e/copilot/single-turn.spec.ts",
      "frontend/e2e/copilot/follow-up.spec.ts",
      "frontend/e2e/copilot/degraded.spec.ts",
    ]) {
      expect(fs.existsSync(path.resolve(process.cwd(), "..", name))).toBe(true);
    }
  });

  test("mock 모드 degraded 배너가 뜬다", async ({ page }) => {
    await mockBaseApis(page);
    await mockCopilotSse(page);
    await page.goto("/?copilot=1&mock_scenario=degraded");
    await submitCopilotQuery(page, "AAPL 최근 뉴스");
    await expect(page.getByTestId("copilot-degraded-card"))
      .toBeVisible({ timeout: 20_000 });
  });
});
