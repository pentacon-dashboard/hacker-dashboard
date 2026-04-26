/**
 * degraded.spec.ts — Copilot degraded 모드 E2E
 *
 * MSW handler 가 step.gate_fail 이벤트를 반환하는 시나리오
 * URL: /?copilot=1&mock_scenario=degraded
 */
import { test, expect } from "@playwright/test";

test.describe("Copilot degraded mode", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?copilot=1&mock_scenario=degraded");
  });

  test("AAPL 최근 뉴스 → degraded 배너 + news_rag_list 카드 렌더", async ({
    page,
  }) => {
    const input = page.getByRole("textbox", { name: "copilot-input" });
    await expect(input).toBeVisible({ timeout: 10_000 });
    await input.fill("AAPL 최근 뉴스");
    await page.keyboard.press("Enter");

    // degraded 카드 표시
    await expect(page.getByTestId("copilot-degraded-card")).toBeVisible({
      timeout: 20_000,
    });

    // 정상 뉴스 RAG 카드도 렌더됨
    await expect(
      page.getByTestId("copilot-card-news_rag_list")
    ).toBeVisible({ timeout: 20_000 });

    // "stub 모드" 또는 "degraded" 배너 텍스트 확인
    await expect(page.getByText(/stub 모드|degraded/i)).toBeVisible({
      timeout: 5_000,
    });
  });
});
