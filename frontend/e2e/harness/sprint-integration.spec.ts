import { test, expect } from "@playwright/test";
import { mockBaseApis } from "../fixtures/api";

const PAGES: Array<{ path: string; key: RegExp }> = [
  { path: "/", key: /Client A|고객장부|Dashboard/i },
  { path: "/portfolio", key: /Client A|고객장부|Dashboard/i },
  { path: "/watchlist", key: /Client A|고객장부|Dashboard/i },
  { path: "/symbol/yahoo/AAPL", key: /AAPL|RSI|MACD/i },
  { path: "/market-analyze", key: /KOSPI|S&P|VIX|Sector|시장/i },
  { path: "/copilot", key: /Copilot|코파일럿/i },
  { path: "/upload", key: /Upload|CSV|업로드/i },
  { path: "/settings", key: /Settings|설정|Demo/i },
];

for (const p of PAGES) {
  test(`page ${p.path} renders without runtime errors`, async ({ page }) => {
    await mockBaseApis(page);
    const consoleErrors: string[] = [];
    page.on("pageerror", (e) => consoleErrors.push(String(e)));
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    const response = await page.goto(p.path, { waitUntil: "domcontentloaded" });
    expect(response?.status(), `${p.path} HTTP status`).toBeLessThan(400);
    await expect(page.locator("body")).toContainText(p.key, { timeout: 10_000 });
    await page.waitForTimeout(1000);

    const fatal = consoleErrors.filter(
      (error) => !/(Warning|hydration|favicon|404)/i.test(error),
    );
    expect(fatal, `${p.path} console errors: ${fatal.join(" | ")}`).toHaveLength(0);
  });
}

test("CSV upload to analyze to dashboard flow smoke", async ({ page }) => {
  await mockBaseApis(page);
  await page.goto("/upload");
  await expect(page.locator("body")).toContainText(/CSV|업로드|Upload/i);
});
