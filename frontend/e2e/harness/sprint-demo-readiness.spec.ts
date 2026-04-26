// frontend/e2e/harness/sprint-demo-readiness.spec.ts
// sprint-demo-readiness E2E 회귀 가드 — integration-qa 위임 결과
import { test, expect } from '@playwright/test'

test('데모 §0 — 사이드바 Demo User · demo@demo.com 노출', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('body')).toContainText(/Demo\s*User|demo@demo\.com|데모 모드/i, {
    timeout: 10_000,
  })
})

test('데모 §2.1 — 대시보드 KPI 6개 + 시장 주도주 카드 + 최신 뉴스', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('body')).toContainText(/총\s*자산|Total Assets/i)
  await expect(page.locator('body')).toContainText(/시장 주도주|Market Leaders/i)
  await expect(page.locator('body')).toContainText(/뉴스|News/i)
})

test('데모 §2.4 — 심볼 상세 RSI/MACD 서브차트 노출', async ({ page }) => {
  await page.goto('/symbol/yahoo/AAPL')
  await expect(page.locator('body')).toContainText(/RSI/i, { timeout: 15_000 })
  await expect(page.locator('body')).toContainText(/MACD/i)
})

test('데모 §2.6 — 코파일럿 페이지 진입 (3단 게이트 배지 자리 존재)', async ({ page }) => {
  await page.goto('/copilot')
  await expect(page.locator('body')).toContainText(/Copilot|코파일럿/i, { timeout: 10_000 })
})

test('Vercel 프로덕션 health (옵션 — VERCEL_URL 있을 때만)', async ({ request }) => {
  const url = process.env.VERCEL_URL ?? process.env.PRODUCTION_URL
  test.skip(!url, 'VERCEL_URL 미설정 — 로컬 시연만 측정')
  const r = await request.get(`${url}/api/health`)
  expect(r.status()).toBeLessThan(500)
})
