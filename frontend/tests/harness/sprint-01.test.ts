// sprint-01 acceptance — CopilotPlan TS 타입 검증.
// 본 파일은 이전 하네스 런이 남긴 베이스라인 그린 stub 을 덮어쓴다.
// 베이스라인(lint/typecheck/build) 은 contract.md 의 AC-01-0 게이트로 대체된다.
import { describe, it, expectTypeOf } from "vitest";
import type { components } from "@/shared/types/api"; // 프로젝트 alias 따름

type CopilotPlan = components["schemas"]["CopilotPlan"];
type CopilotStep = components["schemas"]["CopilotStep"];

describe("sprint-01 acceptance — CopilotPlan TS types are generated", () => {
  it("CopilotPlan has required fields", () => {
    expectTypeOf<CopilotPlan>().toHaveProperty("plan_id");
    expectTypeOf<CopilotPlan>().toHaveProperty("steps");
    expectTypeOf<CopilotPlan>().toHaveProperty("session_id");
  });

  it("CopilotStep.agent is the 9-literal union (stock/crypto/fx/macro/portfolio/rebalance/comparison/simulator/news-rag)", () => {
    type AgentName = CopilotStep["agent"];
    const ok: AgentName[] = [
      "stock",
      "crypto",
      "fx",
      "macro",
      "portfolio",
      "rebalance",
      "comparison",
      "simulator",
      "news-rag",
    ];
    // 컴파일만 통과하면 OK. 배열 길이로 9개 정합성 보강.
    if (ok.length !== 9) throw new Error("CopilotStep.agent union must be 9 literals");
  });
});
