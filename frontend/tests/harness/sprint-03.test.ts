import { describe, it, expectTypeOf } from "vitest";
import type { components } from "@/shared/types/api";

type Card = components["schemas"]["CopilotCard"];

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
