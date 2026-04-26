import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PeriodTabs, PERIOD_DAYS, type PeriodKey } from "./period-tabs";

describe("PeriodTabs", () => {
  it("4개 탭 (1W/1M/3M/1Y) 을 렌더한다", () => {
    render(<PeriodTabs value="1M" onChange={() => {}} />);
    expect(screen.getByRole("tab", { name: "1W" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "1M" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "3M" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "1Y" })).toBeInTheDocument();
  });

  it("현재 value 탭만 aria-selected=true 이다", () => {
    render(<PeriodTabs value="3M" onChange={() => {}} />);
    expect(screen.getByRole("tab", { name: "3M" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "1W" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("탭 클릭 시 onChange 가 해당 키로 호출된다", () => {
    const onChange = vi.fn();
    render(<PeriodTabs value="1M" onChange={onChange} />);

    fireEvent.click(screen.getByRole("tab", { name: "1Y" }));
    expect(onChange).toHaveBeenCalledWith<[PeriodKey]>("1Y");

    fireEvent.click(screen.getByRole("tab", { name: "1W" }));
    expect(onChange).toHaveBeenLastCalledWith<[PeriodKey]>("1W");
  });

  it("PERIOD_DAYS 매핑이 7/30/90/365 이다", () => {
    expect(PERIOD_DAYS["1W"]).toBe(7);
    expect(PERIOD_DAYS["1M"]).toBe(30);
    expect(PERIOD_DAYS["3M"]).toBe(90);
    expect(PERIOD_DAYS["1Y"]).toBe(365);
  });
});
