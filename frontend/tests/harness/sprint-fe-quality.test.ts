import { describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const FRONTEND_DIR = resolve(__dirname, '..', '..')
const REPO_ROOT = resolve(FRONTEND_DIR, '..')

function run(cmd: string, args: string[]): { code: number; stdout: string; stderr: string } {
  try {
    // Windows 에서 npm/npx 는 shell 옵션 없이는 .cmd 파일을 찾지 못하므로 shell: true 사용
    const stdout = execFileSync(cmd, args, {
      cwd: FRONTEND_DIR,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    })
    return { code: 0, stdout, stderr: '' }
  } catch (err: unknown) {
    const e = err as { status?: number; stdout?: string; stderr?: string }
    return { code: e.status ?? 1, stdout: e.stdout ?? '', stderr: e.stderr ?? '' }
  }
}

describe('sprint-fe-quality acceptance', () => {
  it('eslint reports zero warning/error', () => {
    const r = run('npm', ['run', 'lint', '--silent'])
    expect(r.code, `eslint failed:\n${r.stdout}\n${r.stderr}`).toBe(0)
    // ESLint 0 warning 이어야 함 — "warning" 단어가 출력에 등장하면 회귀
    // notification-bell.test.tsx 의 unused waitFor 등 Generator 가 fix 해야 함
    expect(r.stdout.toLowerCase()).not.toMatch(/\d+\s+warning/)
  })

  it('tsc --noEmit clean (strict + noUncheckedIndexedAccess 유지)', () => {
    const r = run('npm', ['run', 'typecheck', '--silent'])
    // next.config.ts TS2353 (eslint key) 는 Generator 가 fix 해야 함
    expect(r.code, `typecheck failed:\n${r.stdout}\n${r.stderr}`).toBe(0)
    const tsconfig = JSON.parse(readFileSync(resolve(FRONTEND_DIR, 'tsconfig.json'), 'utf-8'))
    expect(tsconfig.compilerOptions?.strict).toBe(true)
    expect(tsconfig.compilerOptions?.noUncheckedIndexedAccess).toBe(true)
  })

  it('vitest 271+ tests pass with zero failures', () => {
    // sprint 자기 자신 + sprint-06 (typecheck 케이스 별도 추적) 제외
    // sprint-06 의 typecheck fail 도 이 스프린트 통과의 일부로 보지만, 별도 단언으로 검증.
    const r = run('npx', [
      'vitest',
      'run',
      '--reporter=json',
      '--exclude',
      'tests/harness/sprint-fe-quality.test.ts',
    ])
    expect(r.code, `vitest non-zero exit:\n${r.stdout.slice(-2000)}`).toBe(0)
    const lastBrace = r.stdout.lastIndexOf('}')
    const firstBrace = r.stdout.indexOf('{')
    const json = JSON.parse(r.stdout.slice(firstBrace, lastBrace + 1))
    expect(json.numFailedTests).toBe(0)
    expect(json.numPassedTests).toBeGreaterThanOrEqual(271)
  })

  it('shared/types/api.ts is in sync with shared/openapi.json (regenerate diff = 0)', () => {
    const apiTsPath = resolve(REPO_ROOT, 'shared', 'types', 'api.ts')
    const before = readFileSync(apiTsPath, 'utf-8')
    const r = run('npm', ['run', 'gen:api', '--silent'])
    expect(r.code, `gen:api failed:\n${r.stderr}`).toBe(0)
    const after = readFileSync(apiTsPath, 'utf-8')
    expect(after, 'shared/types/api.ts drift — gen:api 결과가 커밋된 것과 다름').toBe(before)
  })

  it('next-themes provider + dark/light tokens exist (다크모드 회귀 가드)', () => {
    // 실제 ThemeProvider 는 app/providers.tsx 에 위치 (layout.tsx 가 <Providers> 만 렌더)
    const providers = readFileSync(resolve(FRONTEND_DIR, 'app', 'providers.tsx'), 'utf-8')
    expect(providers).toMatch(/ThemeProvider|next-themes/)
    const layout = readFileSync(resolve(FRONTEND_DIR, 'app', 'layout.tsx'), 'utf-8')
    // layout 은 Providers wrapper 로 ThemeProvider 를 간접 사용
    expect(layout).toMatch(/Providers/)
    const globals = readFileSync(resolve(FRONTEND_DIR, 'app', 'globals.css'), 'utf-8')
    expect(globals).toMatch(/\.dark\s*\{/)
  })

  it('all 8 demo pages have a route.tsx or page.tsx', () => {
    const pages = [
      'app/page.tsx', // dashboard
      'app/portfolio/page.tsx',
      'app/watchlist/page.tsx',
      'app/symbol',
      'app/market-analyze/page.tsx',
      'app/copilot/page.tsx',
      'app/upload/page.tsx',
      'app/settings',
    ]
    for (const p of pages) {
      const abs = resolve(FRONTEND_DIR, p)
      expect(existsSync(abs), `데모 페이지 누락: ${p}`).toBe(true)
    }
  })

  it('i18n dict has both ko and en for every key (zero asymmetry)', () => {
    // 실제 dict.ts 구조: flat Record<string, { ko: string; en: string }>
    // 예: "sidebar.dashboard": { ko: "대시보드", en: "Dashboard" }
    // 따라서 각 엔트리에서 ko/en 두 키가 모두 존재하는지 검사한다.
    const dictSrc = readFileSync(resolve(FRONTEND_DIR, 'lib', 'i18n', 'dict.ts'), 'utf-8')
    // 모든 dict 엔트리(키: { ... }) 패턴 추출
    const entryPattern = /["']([\w.\-]+)["']\s*:\s*\{([^{}]*)\}/g
    const entries = [...dictSrc.matchAll(entryPattern)]
    expect(entries.length, 'dict 엔트리를 하나도 추출하지 못함 — 정규식이 실제 구조와 안 맞음').toBeGreaterThan(0)
    const missingKo: string[] = []
    const missingEn: string[] = []
    for (const m of entries) {
      const key = m[1] ?? ''
      const body = m[2] ?? ''
      if (key === '') continue // 매치 그룹 없음 — 건너뜀
      if (!/\bko\s*:/.test(body)) missingKo.push(key)
      if (!/\ben\s*:/.test(body)) missingEn.push(key)
    }
    expect(missingKo, `ko 누락 키: ${missingKo.slice(0, 10).join(', ')}`).toHaveLength(0)
    expect(missingEn, `en 누락 키: ${missingEn.slice(0, 10).join(', ')}`).toHaveLength(0)
  })
})
