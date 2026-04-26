// frontend/tests/harness/sprint-integration.test.ts
import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve, join } from 'node:path'

const FRONTEND_DIR = resolve(__dirname, '..', '..')
const _REPO_ROOT = resolve(FRONTEND_DIR, '..')

describe('sprint-integration FE-side acceptance', () => {
  it('all BE-bound fetch helpers cast to shared/types', () => {
    const apiDir = resolve(FRONTEND_DIR, 'lib', 'api')
    expect(existsSync(apiDir), 'lib/api/ 누락').toBe(true)
    let importsTypes = false
    function walk(dir: string) {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const p = join(dir, entry.name)
        if (entry.isDirectory()) walk(p)
        else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
          const src = readFileSync(p, 'utf-8')
          if (/from ['"][^'"]*shared\/types/.test(src)) importsTypes = true
        }
      }
    }
    walk(apiDir)
    expect(importsTypes, 'lib/api/ 어디에도 shared/types import 없음 — 계약 우회 의심').toBe(true)
  })

  it('vercel.json rewrites point at production BE host', () => {
    const cfg = JSON.parse(readFileSync(resolve(FRONTEND_DIR, 'vercel.json'), 'utf-8'))
    const rewrites = cfg.rewrites ?? []
    expect(rewrites.length).toBeGreaterThan(0)
    const apiRule = rewrites.find((r: { source: string }) => r.source.startsWith('/api/'))
    expect(apiRule, '/api/* rewrite 규칙 누락').toBeTruthy()
    expect(apiRule.destination).toMatch(/^https:\/\/.+\.fly\.dev/)
  })
})
