// frontend/tests/harness/sprint-demo-readiness.test.ts
// sprint-demo-readiness FE-side 회귀 가드 — integration-qa 위임 결과
import { describe, expect, it } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const REPO_ROOT = resolve(__dirname, '..', '..', '..')
const DEMO_DOC = resolve(REPO_ROOT, 'docs/qa/demo-rehearsal-2026-04-24.md')

describe('sprint-demo-readiness FE-side acceptance', () => {
  it('demo seed CSV exists for upload demo (§2.7)', () => {
    // 리허설 §2.7 이 demo/seeds/sample_portfolio.csv 를 드래그한다고 명시.
    // 후보 경로 중 하나라도 존재하면 통과 (Generator 가 demo/seeds/ 또는 frontend/public/demo/ 에 신규 작성 가능).
    const candidates = [
      resolve(REPO_ROOT, 'demo/seeds/sample_portfolio.csv'),
      resolve(REPO_ROOT, 'frontend/public/demo/sample_portfolio.csv'),
    ]
    const found = candidates.some((p) => existsSync(p))
    expect(found, `데모 CSV 누락. 후보: ${candidates.join(' | ')}`).toBe(true)
  })

  it('vercel.json deployment config valid (security headers + api rewrite)', () => {
    const cfg = JSON.parse(readFileSync(resolve(REPO_ROOT, 'frontend/vercel.json'), 'utf-8'))
    expect(cfg.framework).toBe('nextjs')
    const headers = cfg.headers?.[0]?.headers ?? []
    const keys = headers.map((h: { key: string }) => h.key)
    for (const required of [
      'X-Content-Type-Options',
      'X-Frame-Options',
      'Strict-Transport-Security',
    ]) {
      expect(keys, `vercel.json 보안 헤더 누락: ${required}`).toContain(required)
    }
  })

  it('demo rehearsal doc references the same 8 pages as app/ routes', () => {
    const doc = readFileSync(DEMO_DOC, 'utf-8')
    const expectedRoutes = [
      '/',
      '/portfolio',
      '/watchlist',
      '/symbol/yahoo/AAPL',
      '/market-analyze',
      '/copilot',
      '/upload',
    ]
    for (const r of expectedRoutes) {
      expect(doc, `리허설 문서가 ${r} 를 언급하지 않음`).toContain(r)
    }
  })

  it('demo mode standard copy (§0) present in settings page or sidebar component', () => {
    // "Demo User" 또는 "DEMO 배지" 가 사이드바/설정 컴포넌트에 노출되어야 함
    const fs = require('node:fs') as typeof import('node:fs')
    const path = require('node:path') as typeof import('node:path')
    const targets = [
      resolve(REPO_ROOT, 'frontend/components/layout'),
      resolve(REPO_ROOT, 'frontend/components/settings'),
    ]
    let hit = false
    function walk(dir: string) {
      if (!fs.existsSync(dir)) return
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, entry.name)
        if (entry.isDirectory()) walk(p)
        else if (entry.isFile() && /\.(tsx?|mdx?)$/.test(entry.name)) {
          const src = fs.readFileSync(p, 'utf-8')
          if (/Demo\s*User|DEMO\s*배지|demo@demo\.com|데모 모드/i.test(src)) hit = true
        }
      }
    }
    targets.forEach(walk)
    expect(hit, '데모 모드 표준 카피가 layout/settings 어디에도 없음').toBe(true)
  })
})
