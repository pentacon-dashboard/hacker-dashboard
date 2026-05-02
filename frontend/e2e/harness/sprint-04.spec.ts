import { test, expect } from "@playwright/test";
import { mockBaseApis, submitCopilotQuery } from "../fixtures/api";

test.describe("sprint-04 acceptance — command bar + progressive rendering", () => {
  test("⌘K 로 커맨드 바 열고 질의 입력 → drawer 에 카드가 progressive 하게, degraded 포함 나타난다", async ({ page }) => {
    // data-only SSE mock (revision 2: event: 라인 없음)
    await mockBaseApis(page);
    await page.route("**/copilot/query", async (route) => {
      const chunks = [
        `data: ${JSON.stringify({type: "plan.ready", plan: {plan_id: "p", session_id: "s", steps: [
          {step_id: "a", agent: "portfolio", inputs: {}, depends_on: [], gate_policy: {schema: true, domain: true, critique: true}},
          {step_id: "b", agent: "comparison", inputs: {}, depends_on: [], gate_policy: {schema: true, domain: true, critique: true}},
        ], created_at: ""}})}\n\n`,
        `data: ${JSON.stringify({type: "step.start", step_id: "a"})}\n\n`,
        `data: ${JSON.stringify({type: "step.token", step_id: "a", text: "안녕"})}\n\n`,
        `data: ${JSON.stringify({type: "step.result", step_id: "a", card: {type: "text", body: "포트폴리오 요약"}})}\n\n`,
        // BLOCKING-6: degraded 시나리오
        `data: ${JSON.stringify({type: "step.start", step_id: "b"})}\n\n`,
        `data: ${JSON.stringify({type: "step.gate", step_id: "b", gate: "domain", status: "fail", reason: "비교 대상 누락"})}\n\n`,
        `data: ${JSON.stringify({type: "step.result", step_id: "b", card: {type: "text", body: "부분 비교", degraded: true}})}\n\n`,
        `data: ${JSON.stringify({type: "step.gate", step_id: "final", gate: "schema", status: "pass"})}\n\n`,
        `data: ${JSON.stringify({type: "step.gate", step_id: "final", gate: "domain", status: "pass"})}\n\n`,
        `data: ${JSON.stringify({type: "step.gate", step_id: "final", gate: "critique", status: "pass"})}\n\n`,
        `data: ${JSON.stringify({type: "final.card", card: {type: "text", body: "통합 응답"}})}\n\n`,
        `data: ${JSON.stringify({type: "done", session_id: "s", turn_id: "t1"})}\n\n`,
      ];
      await route.fulfill({
        status: 200,
        headers: {
          "content-type": "text/event-stream",
          "x-copilot-session-id": "s",
        },
        body: chunks.join(""),
      });
    });

    await page.goto("/");
    await page.keyboard.press("Control+K");
    await submitCopilotQuery(page, "포트폴리오 요약");

    const drawer = page.getByRole("dialog", { name: /copilot/i });
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText("포트폴리오 요약")).toBeVisible({ timeout: 5_000 });
    // DegradedCard 렌더 확인
    await expect(drawer.getByRole("alert")).toContainText(/비교 대상 누락/);
    await expect(drawer.getByTestId("copilot-card-final").getByText("통합 응답").last()).toBeVisible({ timeout: 5_000 });
  });
});
