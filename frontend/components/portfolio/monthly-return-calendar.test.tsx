import { describe, it, expect } from "vitest";
import { renderWithLocale as render, screen } from "@/lib/test-utils";
import { MonthlyReturnCalendar, type MonthlyReturnCell } from "./monthly-return-calendar";

function buildCells(count: number): MonthlyReturnCell[] {
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(2026, 0, 1 + i);
    const iso = date.toISOString().slice(0, 10);
    const ret = Math.sin(i * 0.3) * 3;
    return {
      date: iso,
      return_pct: ret.toFixed(2),
      cell_level: Math.abs(ret) < 1 ? 0 : Math.abs(ret) < 2 ? 1 : Math.abs(ret) < 3 ? 2 : 3,
    };
  });
}

describe("MonthlyReturnCalendar", () => {
  it("빈 배열이면 empty state를 렌더한다", () => {
    render(<MonthlyReturnCalendar cells={[]} />);
    expect(screen.getByTestId("monthly-return-calendar-empty")).toBeInTheDocument();
  });

  it("365개 셀이 제공되면 캘린더를 렌더한다", () => {
    const cells = buildCells(365);
    render(<MonthlyReturnCalendar cells={cells} year={2026} />);
    expect(screen.getByTestId("monthly-return-calendar")).toBeInTheDocument();
  });

  it("calendar-cell 요소가 존재한다 (365일 시드)", () => {
    const cells = buildCells(365);
    render(<MonthlyReturnCalendar cells={cells} year={2026} />);
    const calCells = screen.getAllByTestId("calendar-cell");
    expect(calCells.length).toBeGreaterThan(300);
  });

  it("월 라벨 Jan이 렌더된다", () => {
    const cells = buildCells(365);
    render(<MonthlyReturnCalendar cells={cells} year={2026} />);
    expect(screen.getByText("Jan")).toBeInTheDocument();
  });

  it("낮음/높음 범례가 렌더된다", () => {
    const cells = buildCells(30);
    render(<MonthlyReturnCalendar cells={cells} year={2026} />);
    expect(screen.getByText("낮음")).toBeInTheDocument();
    expect(screen.getByText("높음")).toBeInTheDocument();
  });
});
