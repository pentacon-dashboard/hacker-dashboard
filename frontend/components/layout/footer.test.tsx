import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppFooter } from "./footer";

describe("AppFooter", () => {
  it("'가격 데이터' 텍스트를 포함하는 문단을 렌더한다", () => {
    render(<AppFooter />);
    expect(screen.getByText(/가격 데이터/)).toBeInTheDocument();
  });

  it("데이터 출처 목록(FinHub)을 렌더한다", () => {
    render(<AppFooter />);
    expect(screen.getByText(/FinHub/)).toBeInTheDocument();
  });

  it("'실시간 지연 약 20분' 텍스트를 렌더한다", () => {
    render(<AppFooter />);
    expect(screen.getByText(/실시간 지연 약 20분/)).toBeInTheDocument();
  });
});
