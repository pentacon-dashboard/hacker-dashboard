import { test, expect } from "@playwright/test";
import { mockBaseApis, mockCopilotSse, submitCopilotQuery } from "../fixtures/api";

test.describe("sprint-05 acceptance - follow-up 대화 UX", () => {
  test("두 번째 질의가 직전 질의의 종목을 유지", async ({ page }) => {
    await mockBaseApis(page);
    await mockCopilotSse(page);
    await page.goto("/");
    await page.keyboard.press("Control+K");

    await submitCopilotQuery(page, "AAPL 분석");
    await expect(page.getByTestId("copilot-drawer")).toContainText(/AAPL/, {
      timeout: 10_000,
    });

    await submitCopilotQuery(page, "그 종목 공시 요약");
    await expect(page.getByTestId("copilot-drawer")).toContainText(/AAPL/, {
      timeout: 15_000,
    });
  });
});
