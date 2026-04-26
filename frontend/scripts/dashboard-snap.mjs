import { chromium } from "playwright";

const url = process.env.URL ?? "http://localhost:3000/";
const out = process.env.OUT ?? "/tmp/dashboard.png";

const browser = await chromium.launch();
// 16:9 (1920×1080) — 데스크탑 표준 뷰포트로 통일
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await ctx.newPage();

await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
// MSW는 브라우저 컨텍스트에서 시작됨 — 워커 등록 후 첫 render 대기
await page.waitForTimeout(1500);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log("screenshot:", out);
