/**
 * single-turn.spec.ts — Copilot 단일 턴 E2E
 *
 * 조건:
 * - NEXT_PUBLIC_COPILOT_MOCK=1 환경에서 MSW SSE mock 사용
 * - 실 FastAPI 기동 불필요
 */
import { test, expect } from "@playwright/test";

test.describe("Copilot single-turn", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/?copilot=1");
  });

  test("TSLA vs NVDA 비교 쿼리 → comparison_table + chart + final 카드 렌더", async ({
    page,
  }) => {
    // Copilot 커맨드바 입력
    const input = page.getByRole("textbox", { name: "copilot-input" });
    await expect(input).toBeVisible({ timeout: 10_000 });
    await input.fill("TSLA vs NVDA 비교");
    await page.keyboard.press("Enter");

    // Drawer 표시
    await expect(page.getByTestId("copilot-drawer")).toBeVisible({
      timeout: 15_000,
    });

    // comparison_table 카드
    await expect(
      page.getByTestId("copilot-card-comparison_table")
    ).toBeVisible({ timeout: 20_000 });

    // chart 카드
    await expect(page.getByTestId("copilot-card-chart")).toBeVisible({
      timeout: 20_000,
    });

    // final 카드 — "종합" 또는 "요약" 텍스트 포함
    await expect(page.getByTestId("copilot-card-final")).toContainText(
      /종합|요약/,
      { timeout: 20_000 }
    );

    // 스크린샷 저장 (docs/screenshots/copilot-query.png)
    await page.screenshot({
      path: "../../docs/screenshots/copilot-query.png",
      fullPage: false,
    });
  });
});
