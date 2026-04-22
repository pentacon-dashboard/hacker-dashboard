import { describe, it, expectTypeOf } from "vitest";
import type { components, paths } from "@shared/types/api"; // @shared/* -> ../shared/*

type Citation = components["schemas"]["Citation"];
type SearchResp = paths["/search/news"]["get"]["responses"]["200"]["content"]["application/json"];

describe("sprint-02 acceptance — RAG types are generated", () => {
  it("Citation has mandatory fields", () => {
    expectTypeOf<Citation>().toHaveProperty("doc_id");
    expectTypeOf<Citation>().toHaveProperty("chunk_id");
    expectTypeOf<Citation>().toHaveProperty("source_url");
    expectTypeOf<Citation>().toHaveProperty("title");
    expectTypeOf<Citation>().toHaveProperty("published_at");
    expectTypeOf<Citation>().toHaveProperty("excerpt");
    expectTypeOf<Citation>().toHaveProperty("score");
  });

  it("GET /search/news returns Citation[]", () => {
    expectTypeOf<SearchResp>().toEqualTypeOf<Citation[]>();
  });
});
