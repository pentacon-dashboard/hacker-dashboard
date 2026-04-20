import { test, expect } from "@playwright/test";

/**
 * 스모크 테스트 — 핵심 렌더 + 다크모드 + BE 헬스체크.
 *
 * 셀렉터는 의도적으로 느슨하게 — FE 팀이 헤더 문구를 변경해도 깨지지 않도록.
 * - 시나리오 1: 루트 페이지가 렌더되고 메인 컨텐츠 영역이 보이는지
 * - 시나리오 2: 다크모드 토글이 <html> 의 dark 클래스를 토글하는지
 * - 시나리오 3: BE /health 가 200 을 반환하는지
 */

const BE_BASE = process.env.BE_BASE ?? "http://localhost:8000";

// ── 시나리오 1: 루트 페이지 렌더 ────────────────────────────────────────────
test("루트 페이지가 렌더되고 주요 영역이 보인다", async ({ page }) => {
  await page.goto("/");

  // <main> 또는 id=main-content 또는 role=main 중 하나라도 있으면 OK
  const mainArea = page
    .locator("main, [id='main-content'], [role='main']")
    .first();
  await expect(mainArea).toBeVisible({ timeout: 10_000 });

  // 페이지 타이틀이 비어 있지 않음 (SEO 기본 체크)
  const title = await page.title();
  expect(title.length).toBeGreaterThan(0);
});

// ── 시나리오 2: 다크모드 토글 ────────────────────────────────────────────────
test("다크모드 토글이 html.dark 클래스를 토글한다", async ({ page }) => {
  await page.goto("/");

  // 다크모드 토글 버튼: aria-label 또는 data-testid 기반으로 탐색
  // FE 팀 구현에 따라 aria-label 이 다를 수 있으므로 복수 셀렉터 시도
  const toggle = page
    .locator(
      [
        "button[aria-label*='dark']",
        "button[aria-label*='Dark']",
        "button[aria-label*='theme']",
        "button[aria-label*='Theme']",
        "[data-testid='theme-toggle']",
        "[data-testid='dark-mode-toggle']",
      ].join(", ")
    )
    .first();

  // 토글 버튼이 없으면 테스트 skip (FE 미구현 단계 허용)
  const toggleExists = await toggle.count();
  if (toggleExists === 0) {
    test.skip();
    return;
  }

  // 토글 전 상태 기록
  const htmlEl = page.locator("html");
  const beforeDark = await htmlEl.getAttribute("class");
  const wasDark = (beforeDark ?? "").includes("dark");

  await toggle.click();
  await page.waitForTimeout(300); // CSS 트랜지션 여유

  const afterClass = await htmlEl.getAttribute("class");
  const isDarkNow = (afterClass ?? "").includes("dark");

  // 클릭 전후 dark 상태가 반전되어야 함
  expect(isDarkNow).toBe(!wasDark);
});

// ── 시나리오 3: Backend /health 200 ─────────────────────────────────────────
test("BE /health 엔드포인트가 200을 반환한다", async ({ request }) => {
  const response = await request.get(`${BE_BASE}/health`, {
    timeout: 10_000,
  });

  expect(response.status()).toBe(200);

  // 응답 바디가 JSON 이라면 status 필드 확인 (선택적)
  const contentType = response.headers()["content-type"] ?? "";
  if (contentType.includes("application/json")) {
    const body = await response.json();
    // { "status": "ok" } 또는 { "status": "healthy" } 중 하나
    expect(["ok", "healthy", "up"]).toContain(
      (body as { status?: string }).status
    );
  }
});
