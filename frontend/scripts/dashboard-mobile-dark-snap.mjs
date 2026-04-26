/**
 * dashboard-mobile-dark-snap.mjs
 *
 * 모바일/다크모드 스폿체크용 스크린샷 캡처 스크립트.
 *
 * 캡처 대상 3장:
 *   - dashboard-mobile-375.png  : viewport 375x812 (iPhone SE)
 *   - dashboard-dark.png        : 1920x1080 (16:9), dark 클래스 주입
 *   - dashboard-dark-mobile.png : 375x812 + dark 클래스 주입
 *
 * 실행:
 *   NEXT_PUBLIC_COPILOT_MOCK=1 npm run dev &  # dev 서버가 이미 켜져 있어야 함
 *   node scripts/dashboard-mobile-dark-snap.mjs
 *
 * 환경변수:
 *   URL  — 캡처할 주소 (기본: http://localhost:3000/)
 *   OUT  — 출력 디렉터리 (기본: C:/Users/ehgus/AppData/Local/Temp)
 */

import { chromium } from "playwright";
import path from "path";

const url = process.env.URL ?? "http://localhost:3000/";
const outDir = process.env.OUT ?? "C:/Users/ehgus/AppData/Local/Temp";

/** MSW 등록 + 첫 렌더 완료 대기 */
async function waitForDashboard(page) {
  await page.goto(url, { waitUntil: "networkidle", timeout: 30_000 });
  // MSW 워커 등록 후 첫 번째 API 응답이 처리될 때까지 추가 대기
  await page.waitForTimeout(2_000);
}

async function main() {
  const browser = await chromium.launch();

  // ── 1. 모바일 375x812 (iPhone SE), 라이트 모드 ───────────────────────────
  {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await ctx.newPage();
    await waitForDashboard(page);
    const out = path.join(outDir, "dashboard-mobile-375.png");
    await page.screenshot({ path: out, fullPage: true });
    console.log("captured:", out);
    await ctx.close();
  }

  // ── 2. 데스크탑 1920x1080 (16:9), 다크 모드 ─────────────────────────────
  {
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await ctx.newPage();
    await waitForDashboard(page);
    // dark 클래스 강제 주입 (next-themes 가 localStorage 기반이므로 직접 DOM 조작)
    await page.evaluate(() => {
      document.documentElement.classList.add("dark");
    });
    await page.waitForTimeout(500); // CSS 전환 여유
    const out = path.join(outDir, "dashboard-dark.png");
    await page.screenshot({ path: out, fullPage: true });
    console.log("captured:", out);
    await ctx.close();
  }

  // ── 3. 모바일 375x812, 다크 모드 ─────────────────────────────────────────
  {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await ctx.newPage();
    await waitForDashboard(page);
    await page.evaluate(() => {
      document.documentElement.classList.add("dark");
    });
    await page.waitForTimeout(500);
    const out = path.join(outDir, "dashboard-dark-mobile.png");
    await page.screenshot({ path: out, fullPage: true });
    console.log("captured:", out);
    await ctx.close();
  }

  await browser.close();
  console.log("all screenshots saved to:", outDir);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
