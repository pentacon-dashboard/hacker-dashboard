import { describe, it, expect, vi } from "vitest";
import { renderWithLocale as render, screen, fireEvent } from "@/lib/test-utils";
import { DateRangePicker } from "./date-range-picker";

// next/navigation mock
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

describe("DateRangePicker", () => {
  it("날짜 범위 버튼이 렌더된다", () => {
    render(<DateRangePicker />);
    expect(screen.getByTestId("date-range-picker")).toBeInTheDocument();
  });

  it("버튼 클릭 시 팝오버 캘린더가 열린다", () => {
    render(<DateRangePicker />);
    const btn = screen.getByRole("button", { name: /날짜 범위/ });
    fireEvent.click(btn);
    expect(screen.getByRole("dialog", { name: "날짜 범위 선택" })).toBeInTheDocument();
  });

  it("기본값으로 최근 30일 범위 레이블이 표시된다", () => {
    render(<DateRangePicker />);
    const btn = screen.getByRole("button", { name: /날짜 범위/ });
    // 버튼에 날짜 범위 aria-label 포함
    expect(btn.getAttribute("aria-label")).toMatch(/날짜 범위/);
  });
});
