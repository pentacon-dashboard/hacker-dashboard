import { chromium } from "playwright";

const url = process.env.URL ?? "http://localhost:3000/";
const out = process.env.OUT ?? "/tmp/dashboard.png";

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
// MSW는 브라우저 컨텍스트에서 시작됨 — 워커 등록 후 첫 render 대기
await page.waitForTimeout(1500);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log("screenshot:", out);
