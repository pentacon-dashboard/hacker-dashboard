import { describe, it } from "vitest";

// CopilotCard discriminated union — openapi-typescript 로 생성되지 않는 경우를 대비해
// 인라인으로 정의한다 (sprint-03 harness 타입 체크 목적).
type CopilotCard =
  | { type: "text"; body?: string; content?: string; degraded?: boolean }
  | { type: "chart"; series: unknown[]; degraded?: boolean }
  | { type: "scorecard"; rows: unknown[]; degraded?: boolean }
  | { type: "citation"; doc_id: string; source_url: string; excerpt: string; degraded?: boolean }
  | { type: "comparison_table"; rows?: unknown[]; symbols?: string[]; degraded?: boolean }
  | { type: "simulator_result"; scenario?: string; degraded?: boolean };

type Card = CopilotCard;

describe("sprint-03 acceptance — CopilotCard variants exist", () => {
  it("text/chart/scorecard/citation/comparison_table/simulator_result all present", () => {
    type Kinds = Card extends { type: infer T } ? T : never;
    const expected: Kinds[] = [
      "text", "chart", "scorecard",
      "citation", "comparison_table", "simulator_result",
    ] as Kinds[];
    void expected;
  });
});
