import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { CsvMappingCandidateGroup } from "@/lib/portfolio/upload-import";
import { MappingReviewCard } from "./mapping-review-card";

describe("MappingReviewCard", () => {
  it("allows confirmation with only symbol and quantity core mappings", () => {
    const candidates: CsvMappingCandidateGroup[] = [
      {
        standard_field: "symbol",
        candidates: [
          {
            type: "column",
            column: "Ticker",
            confidence: 0.98,
            needs_review: false,
            reason: "known alias for symbol",
          },
        ],
      },
      {
        standard_field: "quantity",
        candidates: [
          {
            type: "column",
            column: "Shares",
            confidence: 0.98,
            needs_review: false,
            reason: "known alias for quantity",
          },
        ],
      },
      { standard_field: "avg_cost", candidates: [] },
      { standard_field: "currency", candidates: [] },
      { standard_field: "market", candidates: [] },
    ];
    const onConfirm = vi.fn();

    render(
      <MappingReviewCard
        candidates={candidates}
        normalizedPreview={[{ source_row: 2, symbol: "AAPL", quantity: "3" }]}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByText(/필수 코어 필드는 Symbol과 Quantity/)).toBeInTheDocument();
    expect(screen.queryByText(/필수 5개/)).not.toBeInTheDocument();
    expect(screen.getByTestId("confirm-mapping-import")).not.toBeDisabled();

    fireEvent.click(screen.getByTestId("confirm-mapping-import"));

    expect(onConfirm).toHaveBeenCalledWith({
      symbol: { type: "column", column: "Ticker" },
      quantity: { type: "column", column: "Shares" },
    });
  });
});
