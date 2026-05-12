import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { ValidationCard } from "./validation-card";

describe("ValidationCard", () => {
  it("shows compact row classification counts when ledger rows are present", () => {
    renderWithProviders(
      <ValidationCard
        result={{
          upload_id: "upload-partial",
          total_rows: 5,
          valid_rows: 2,
          error_rows: 2,
          warning_rows: 1,
          import_status: "partial_imported",
          columns_detected: ["code", "quantity"],
          preview_rows: [{ code: "AAPL", quantity: "1" }],
          imported_rows: [
            {
              classification: "imported",
              source_row: 2,
              reason_code: "ok",
              message: "imported",
            },
            {
              classification: "imported",
              source_row: 3,
              reason_code: "ok",
              message: "imported",
            },
          ],
          recoverable_rows: [
            {
              classification: "recoverable",
              source_row: 4,
              reason_code: "missing_cost_basis",
              message: "needs review",
            },
          ],
          quarantined_rows: [
            {
              classification: "quarantined",
              source_row: 5,
              reason_code: "invalid_quantity",
              message: "quarantined",
            },
          ],
          garbage_rows: [
            {
              classification: "garbage",
              source_row: 6,
              reason_code: "empty",
              message: "ignored",
            },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("validation-row-classification-counts")).toBeInTheDocument();
    expect(screen.getByTestId("validation-imported-count")).toHaveTextContent("2");
    expect(screen.getByTestId("validation-review-count")).toHaveTextContent("1");
    expect(screen.getByTestId("validation-quarantine-count")).toHaveTextContent("1");
    expect(screen.getByTestId("validation-garbage-count")).toHaveTextContent("1");
  });
});
