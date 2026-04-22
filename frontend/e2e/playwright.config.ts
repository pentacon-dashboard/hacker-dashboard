import { defineConfig, devices } from "@playwright/test";

/**
 * E2E 설정.
 *
 * CI 환경(CI=true)에서는 Docker Compose 로 전체 스택이 올라와 있다고 가정 —
 * webServer 를 통해 dev 서버를 자동 기동하는 건 로컬 전용.
 *
 * 베이스 URL 우선순위: E2E_BASE 환경변수 > http://localhost:3000
 */

const isCI = !!process.env.CI;
const baseURL = process.env.E2E_BASE ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./",
  testMatch: "**/*.spec.ts",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: 1,
  workers: isCI ? 2 : undefined,
  reporter: [
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["junit", { outputFile: "playwright-results.xml" }],
    isCI ? ["github"] : ["list"],
  ],

  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // 로컬 개발: Next.js dev 서버를 자동으로 기동
  // CI 는 Docker Compose 전제이므로 webServer 블록 자체를 생략
  // NEXT_PUBLIC_COPILOT_MOCK=1 주입: MSW SSE mock 활성화 (실 FastAPI 기동 불필요)
  ...(!isCI && {
    webServer: {
      command: "NEXT_PUBLIC_COPILOT_MOCK=1 npm run dev",
      url: baseURL,
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_COPILOT_MOCK: "1",
      },
    },
  }),
});
