import { describe, expect, it } from "vitest";
import { renderWithLocale as render, screen } from "@/lib/test-utils";
import { SectorKpiGrid, type SectorItem } from "./sector-kpi-grid";

const MOCK_SECTORS: SectorItem[] = [
  {
    name: "Information Technology",
    change_pct: "-1.51",
    constituents: 92,
    leaders: ["AAPL", "MSFT"],
  },
  {
    name: "Healthcare",
    change_pct: "1.96",
    constituents: 58,
    leaders: ["LLY"],
  },
  {
    name: "Utilities",
    change_pct: "0.11",
    constituents: 30,
    leaders: ["NEE"],
  },
];

describe("SectorKpiGrid", () => {
  it("uses a full-height layout with roomy rows that scale inside the dashboard grid", () => {
    render(<SectorKpiGrid sectors={MOCK_SECTORS} />);

    expect(screen.getByTestId("sector-kpi-grid")).toHaveClass(
      "flex",
      "h-full",
      "min-h-[21rem]",
      "flex-col",
    );
    expect(screen.getByTestId("sector-kpi-list")).toHaveClass(
      "grid",
      "flex-1",
      "auto-rows-fr",
    );

    const row = screen.getByTestId("sector-Information Technology");
    expect(row).toHaveClass("grid", "min-h-8", "items-center");
    expect(row).toHaveAttribute("aria-label", expect.stringContaining("-1.51%"));
    expect(screen.getByTestId("sector-bar-Information Technology")).toHaveClass("h-5");
  });

  it("keeps sector names, values, and trend direction visible", () => {
    render(<SectorKpiGrid sectors={MOCK_SECTORS} />);

    expect(screen.getByText("정보기술")).toBeInTheDocument();
    expect(screen.getByText("헬스케어")).toBeInTheDocument();
    expect(screen.getByText("-1.51%")).toBeInTheDocument();
    expect(screen.getByText("+1.96%")).toBeInTheDocument();
    expect(screen.getByTestId("sector-Healthcare")).toHaveAttribute(
      "aria-label",
      expect.stringContaining("+1.96%"),
    );
  });
});
