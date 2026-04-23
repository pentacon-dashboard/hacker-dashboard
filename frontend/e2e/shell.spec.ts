import { test, expect } from "@playwright/test";

/**
 * shell.spec.ts — Phase A-0 공통 쉘 E2E 검증.
 *
 * 검증 항목:
 * 1. 홈에서 8개 nav 항목 존재 확인
 * 2. 사이드바 접힘 토글 동작
 * 3. CSV 버튼 클릭 시 /upload 네비게이션
 * 4. 풋터 "가격 데이터" 텍스트 노출
 */

const NAV_LABELS = [
  "대시보드",
  "포트폴리오",
  "워치리스트",
  "종목 분석",
  "시장 분석",
  "코파일럿",
  "업로드 & 분석",
  "설정",
];

test.describe("공통 쉘 — Phase A-0", () => {
  test.beforeEach(async ({ page }) => {
    // 다크모드 설정
    await page.addInitScript(() => {
      localStorage.setItem("hd-theme", "dark");
    });
    await page.goto("/");
  });

  test("홈에서 8개 nav 항목이 모두 표시된다", async ({ page }) => {
    // 데스크탑 사이드바 (md 이상) 기준
    const sidebar = page.getByRole("complementary", { name: "메인 내비게이션" }).first();

    for (const label of NAV_LABELS) {
      await expect(sidebar.getByText(label)).toBeVisible();
    }
  });

  test("사이드바 접기 버튼 클릭 시 레이블이 숨겨진다", async ({ page }) => {
    // 펼침 상태에서 "대시보드" 텍스트 보임
    const sidebar = page.locator("aside[aria-label='메인 내비게이션']");
    await expect(sidebar.getByText("대시보드")).toBeVisible();

    // 접기 버튼 클릭
    await sidebar.getByRole("button", { name: "사이드바 접기" }).click();

    // 접힘 상태에서 "대시보드" 텍스트 사라짐
    await expect(sidebar.getByText("대시보드")).not.toBeVisible();
  });

  test("CSV 업로드 버튼 클릭 시 /upload 로 이동한다", async ({ page }) => {
    await page.getByTestId("csv-upload-button").click();
    await expect(page).toHaveURL(/\/upload/);
    await expect(page.getByRole("heading", { name: "업로드" })).toBeVisible();
  });

  test("풋터에 '가격 데이터' 텍스트가 표시된다", async ({ page }) => {
    await expect(page.getByTestId("app-footer")).toBeVisible();
    await expect(page.getByText(/가격 데이터/)).toBeVisible();
  });
});
