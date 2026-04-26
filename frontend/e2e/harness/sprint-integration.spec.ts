// frontend/e2e/harness/sprint-integration.spec.ts
import { test, expect } from '@playwright/test'

const PAGES: Array<{ path: string; key: RegExp }> = [
  { path: '/', key: /총\s*자산|Total Assets|Dashboard/i },
  { path: '/portfolio', key: /포트폴리오|Portfolio/i },
  { path: '/watchlist', key: /워치리스트|Watchlist/i },
  { path: '/symbol/yahoo/AAPL', key: /AAPL|RSI|MACD/i },
  { path: '/market-analyze', key: /KOSPI|S&P|VIX|섹터|Sector/i },
  { path: '/copilot', key: /Copilot|코파일럿/i },
  { path: '/upload', key: /업로드|Upload|CSV/i },
  { path: '/settings', key: /설정|Settings|연결된 계정|Demo/i },
]

for (const p of PAGES) {
  test(`page ${p.path} renders without runtime errors`, async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('pageerror', (e) => consoleErrors.push(String(e)))
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })
    const resp = await page.goto(p.path, { waitUntil: 'domcontentloaded' })
    expect(resp?.status(), `${p.path} HTTP status`).toBeLessThan(400)
    await expect(page.locator('body')).toContainText(p.key, { timeout: 10_000 })
    // hydration 후 1s 대기로 client error 캡처
    await page.waitForTimeout(1000)
    const fatal = consoleErrors.filter((e) => !/(Warning|hydration|favicon|404)/i.test(e))
    expect(fatal, `${p.path} 콘솔 에러: ${fatal.join(' | ')}`).toHaveLength(0)
  })
}

test('CSV upload → analyze → dashboard 전환 flow (smoke)', async ({ page }) => {
  await page.goto('/upload')
  await expect(page.locator('body')).toContainText(/CSV|업로드|Upload/i)
  // 실제 업로드 시나리오는 e2e/upload.spec 가 더 깊게 검증. 본 stub 은 진입만.
})
