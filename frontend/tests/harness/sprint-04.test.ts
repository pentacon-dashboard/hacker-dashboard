import { describe, it, expect } from "vitest";
import { copilotStreamReducer, initialCopilotState } from
  "@/hooks/use-copilot-stream";
import type { CopilotEvent } from "@/hooks/use-copilot-stream";

describe("sprint-04 acceptance — copilot stream reducer", () => {
  it("plan.ready stores the plan", () => {
    const s1 = copilotStreamReducer(initialCopilotState, {
      type: "plan.ready",
      plan: { plan_id: "p1", session_id: "s1", steps: [], created_at: "" },
    } as CopilotEvent);
    expect(s1.plan?.plan_id).toBe("p1");
  });

  it("step.token appends to the step buffer", () => {
    let s = copilotStreamReducer(initialCopilotState, {
      type: "step.start", step_id: "a",
    } as CopilotEvent);
    s = copilotStreamReducer(s, { type: "step.token", step_id: "a", text: "Hel" } as CopilotEvent);
    s = copilotStreamReducer(s, { type: "step.token", step_id: "a", text: "lo" } as CopilotEvent);
    expect(s.steps["a"].buffer).toBe("Hello");
  });

  it("step.result swaps buffer with card", () => {
    let s = copilotStreamReducer(initialCopilotState, {
      type: "step.start", step_id: "a",
    } as CopilotEvent);
    s = copilotStreamReducer(s, {
      type: "step.result", step_id: "a",
      card: { type: "text", body: "done" },
    } as CopilotEvent);
    expect(s.steps["a"].card?.type).toBe("text");
  });

  it("step.gate fail marks step degraded and exposes reducer-level degraded state", () => {
    // BLOCKING-6 degraded 경로 케이스
    let s = copilotStreamReducer(initialCopilotState, {
      type: "step.start", step_id: "a",
    } as CopilotEvent);
    s = copilotStreamReducer(s, {
      type: "step.gate", step_id: "a", gate: "domain", status: "fail",
      reason: "price out of range",
    } as CopilotEvent);
    s = copilotStreamReducer(s, {
      type: "step.result", step_id: "a",
      card: { type: "text", body: "partial", degraded: true },
    } as CopilotEvent);
    expect(s.steps["a"].degraded).toBe(true);
    expect(s.degraded?.step_id).toBe("a");
    expect(s.degraded?.reason).toMatch(/price out of range/);
  });

  it("final.card + done transitions to completed", () => {
    let s = copilotStreamReducer(initialCopilotState, {
      type: "final.card",
      card: { type: "text", body: "summary" },
    } as CopilotEvent);
    s = copilotStreamReducer(s, {
      type: "done", session_id: "s1", turn_id: "t1",
    } as CopilotEvent);
    expect(s.status).toBe("completed");
    expect(s.finalCard?.type).toBe("text");
    expect(s.turnId).toBe("t1");
    expect(s.sessionId).toBe("s1");
  });
});
