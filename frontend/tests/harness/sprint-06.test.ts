import { describe, it, expect } from "vitest";
import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const FE_ROOT = resolve(__dirname, "..", "..");
const run = (cmd: string, timeout = 300_000) =>
  execSync(cmd, { cwd: FE_ROOT, stdio: "pipe", timeout });

describe("sprint-06 acceptance — full FE ci green", () => {
  it("lint + typecheck + unit tests + build all pass", () => {
    run("npm run lint");
    run("npm run typecheck");
    run("npm run test -- --run");
    run("npm run build");
  });

  it("test:e2e npm script exists", () => {
    const pkg = JSON.parse(readFileSync(resolve(FE_ROOT, "package.json"), "utf-8"));
    expect(pkg.scripts?.["test:e2e"]).toMatch(/^playwright test/);
  });

  it("copilot e2e spec files exist", () => {
    for (const name of [
      "e2e/copilot/single-turn.spec.ts",
      "e2e/copilot/follow-up.spec.ts",
      "e2e/copilot/degraded.spec.ts",
    ]) {
      expect(existsSync(resolve(FE_ROOT, name))).toBe(true);
    }
  });
});
