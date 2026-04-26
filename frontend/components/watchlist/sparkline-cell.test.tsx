import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { SparklineCell } from "./sparkline-cell";

describe("SparklineCell", () => {
  it("유효한 데이터로 SVG를 렌더한다", () => {
    const { container } = render(<SparklineCell data={[1, 2, 3, 2, 4, 3, 5]} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg?.getAttribute("aria-label")).toBe("7일 스파크라인");
  });

  it("빈 배열이면 SVG 없이 fallback을 렌더한다", () => {
    const { container } = render(<SparklineCell data={[]} />);
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("데이터 1개이면 fallback을 렌더한다", () => {
    const { container } = render(<SparklineCell data={[5]} />);
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("상승 추세면 emerald stroke를 사용한다", () => {
    const { container } = render(<SparklineCell data={[1, 2, 3, 4, 5, 6, 7]} />);
    const polyline = container.querySelector("polyline");
    expect(polyline?.getAttribute("stroke")).toBe("#10b981");
  });

  it("하락 추세면 red stroke를 사용한다", () => {
    const { container } = render(<SparklineCell data={[7, 6, 5, 4, 3, 2, 1]} />);
    const polyline = container.querySelector("polyline");
    expect(polyline?.getAttribute("stroke")).toBe("#ef4444");
  });
});
