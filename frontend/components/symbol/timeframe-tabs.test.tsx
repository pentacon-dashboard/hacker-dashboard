import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { TimeframeTabs } from "./timeframe-tabs";

describe("TimeframeTabs", () => {
  it("7개 탭 버튼을 렌더한다", () => {
    renderWithProviders(<TimeframeTabs value="day" onChange={() => {}} />);
    expect(screen.getByTestId("timeframe-tab-1m")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-5m")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-15m")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-60m")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-day")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-week")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-tab-month")).toBeInTheDocument();
  });

  it("선택된 탭은 aria-selected=true이다", () => {
    renderWithProviders(<TimeframeTabs value="day" onChange={() => {}} />);
    expect(screen.getByTestId("timeframe-tab-day")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("timeframe-tab-1m")).toHaveAttribute("aria-selected", "false");
  });

  it("탭 클릭 시 onChange가 호출된다", () => {
    const onChange = vi.fn();
    renderWithProviders(<TimeframeTabs value="day" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("timeframe-tab-1m"));
    expect(onChange).toHaveBeenCalledWith("1m");
  });

  it("tablist role이 설정된다", () => {
    renderWithProviders(<TimeframeTabs value="week" onChange={() => {}} />);
    expect(screen.getByRole("tablist")).toBeInTheDocument();
  });
});
