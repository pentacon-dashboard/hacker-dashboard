/**
 * follow-up.spec.ts — Copilot 2-턴 follow-up E2E
 *
 * 1턴: "TSLA vs NVDA 비교" → comparison_table 렌더 대기
 * 2턴: "그럼 엔비디아 -30% 시 내 포트폴리오?" → simulator_result 렌더
 * 1턴 카드가 히스토리에 유지되는지 검증
 */
import { test, expect } from "@playwright/test";
import { mockBaseApis, mockCopilotSse, submitCopilotQuery } from "../fixtures/api";

test.describe("Copilot follow-up (2-turn)", () => {
  test.beforeEach(async ({ page }) => {
    await mockBaseApis(page);
    await mockCopilotSse(page);
    await page.goto("/?copilot=1");
  });

  test("1턴 비교 후 2턴 시뮬레이터 — 히스토리 카드 유지", async ({ page }) => {
    // 1턴
    await submitCopilotQuery(page, "TSLA vs NVDA 비교");
    await expect(
      page.getByTestId("copilot-card-comparison_table")
    ).toBeVisible({ timeout: 20_000 });

    // 2턴 — same drawer
    await submitCopilotQuery(page, "그럼 엔비디아 -30% 시 내 포트폴리오?");

    // simulator_result 카드 등장
    await expect(
      page.getByTestId("copilot-card-simulator_result")
    ).toBeVisible({ timeout: 20_000 });

    // 1턴 comparison_table 카드가 히스토리에 남아 있어야 함
    await expect(
      page.getByTestId("copilot-card-comparison_table")
    ).toBeVisible({ timeout: 5_000 });

    // 스크린샷 저장 (docs/screenshots/copilot-final-card.png)
    await page.screenshot({
      path: "../../docs/screenshots/copilot-final-card.png",
      fullPage: false,
    });
  });
});
