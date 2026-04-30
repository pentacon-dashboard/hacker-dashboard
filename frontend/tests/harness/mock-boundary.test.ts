import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("live API mock boundaries", () => {
  it("keeps the browser MSW worker scoped to customer portfolio demo handlers", () => {
    const worker = source("tests/mocks/browser.ts");

    expect(worker).toContain('from "./dashboard"');
    expect(worker).not.toMatch(/from\s+["']\.\/copilot-sse["']/);
    expect(worker).not.toMatch(/from\s+["']\.\/copilot-sessions["']/);
    expect(worker).not.toMatch(/from\s+["']\.\/market["']/);
    expect(worker).not.toMatch(/from\s+["']\.\/watchlist["']/);
    expect(worker).not.toMatch(/from\s+["']\.\/settings["']/);
    expect(worker).not.toMatch(/from\s+["']\.\/upload["']/);
  });

  it("does not let Copilot mock flags enable global browser MSW", () => {
    const provider = source("components/providers/msw-provider.tsx");

    expect(provider).toContain("NEXT_PUBLIC_CLIENT_MOCK");
    expect(provider).toContain("NEXT_PUBLIC_USE_MSW_WORKER");
    expect(provider).not.toContain("NEXT_PUBLIC_COPILOT_MOCK");
    expect(provider).not.toContain("COPILOT_MOCK");
  });

  it("keeps Copilot query as a real backend proxy, not a local mock stream", () => {
    const route = source("app/api/copilot/query/route.ts");
    const streamHook = source("hooks/use-copilot-stream.ts");

    expect(route).toContain("BACKEND_API_BASE");
    expect(route).toContain("/copilot/query");
    expect(route).not.toContain("NEXT_PUBLIC_COPILOT_MOCK");
    expect(route).not.toContain("COPILOT_MOCK");
    expect(route).not.toContain("buildNormalStream");
    expect(route).not.toContain("buildDegradedStream");
    expect(route).not.toContain("mock_scenario");
    expect(streamHook).not.toContain("mock_scenario");
  });

  it("does not disable realtime quotes because customer demo mocks are enabled", () => {
    const realtime = source("lib/realtime/use-realtime-ticker.ts");

    expect(realtime).toContain("NEXT_PUBLIC_DISABLE_REALTIME_WS");
    expect(realtime).not.toContain("NEXT_PUBLIC_COPILOT_MOCK");
    expect(realtime).not.toContain("NEXT_PUBLIC_USE_MSW_WORKER");
  });
});
