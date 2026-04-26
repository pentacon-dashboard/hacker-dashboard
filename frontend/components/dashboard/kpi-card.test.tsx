import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiCard } from "./kpi-card";

describe("KpiCard", () => {
  it("label과 value를 렌더한다", () => {
    render(<KpiCard label="총자산" value="₩18.76M" />);
    expect(screen.getByText("총자산")).toBeInTheDocument();
    expect(screen.getByText("₩18.76M")).toBeInTheDocument();
  });

  it("icon prop이 있을 때 아이콘 컨테이너를 렌더한다", () => {
    const { container } = render(
      <KpiCard
        label="수익률"
        value="+4.77%"
        icon={<svg data-testid="kpi-icon" />}
        accent="green"
      />,
    );
    expect(screen.getByTestId("kpi-icon")).toBeInTheDocument();
    // accent=green 이면 emerald 계열 클래스 적용
    const iconWrap = container.querySelector('[aria-hidden="true"]');
    expect(iconWrap?.className).toMatch(/bg-emerald-100/);
  });

  it("icon 이 없으면 아이콘 컨테이너를 렌더하지 않는다", () => {
    const { container } = render(<KpiCard label="종목 수" value="23" />);
    expect(
      container.querySelector('[aria-hidden="true"]'),
    ).not.toBeInTheDocument();
  });

  it("accent prop 별로 배경 클래스가 다르게 매핑된다", () => {
    const cases: Array<{ accent: "blue" | "amber" | "rose" | "violet" | "slate"; expectSubstring: string }> = [
      { accent: "blue", expectSubstring: "blue" },
      { accent: "amber", expectSubstring: "amber" },
      { accent: "rose", expectSubstring: "rose" },
      // violet accent 는 테마 accent 를 따라가도록 bg-primary 토큰 매핑됨 (accent 팔레트 반영)
      { accent: "violet", expectSubstring: "primary" },
      { accent: "slate", expectSubstring: "slate" },
    ];
    for (const { accent, expectSubstring } of cases) {
      const { container } = render(
        <KpiCard
          label="x"
          value="y"
          icon={<span data-testid={`i-${accent}`} />}
          accent={accent}
        />,
      );
      const wrap = container.querySelector('[aria-hidden="true"]');
      expect(wrap?.className).toContain(expectSubstring);
    }
  });

  it("deltaValue 양수이면 초록, 음수이면 빨강 색 클래스를 적용한다", () => {
    const { rerender, container } = render(
      <KpiCard label="일일" value="₩373K" delta="+2.04%" deltaValue={2.04} />,
    );
    const posSpan = container.querySelector("span.shrink-0.text-xs");
    expect(posSpan?.className).toMatch(/green/);

    rerender(
      <KpiCard label="일일" value="-₩500" delta="-0.03%" deltaValue={-0.03} />,
    );
    const negSpan = container.querySelector("span.shrink-0.text-xs");
    expect(negSpan?.className).toMatch(/red/);
  });

  it("testId prop이 data-testid 로 투영된다", () => {
    render(<KpiCard label="x" value="y" testId="kpi-total" />);
    expect(screen.getByTestId("kpi-total")).toBeInTheDocument();
  });
});
