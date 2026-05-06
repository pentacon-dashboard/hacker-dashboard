import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/tests/helpers/render-with-providers";

import { KpiCard } from "./kpi-card";

describe("KpiCard", () => {
  it("renders as a non-interactive card by default", () => {
    renderWithProviders(
      <KpiCard label="총자산" value="₩1.00B" testId="plain-kpi" />,
    );

    expect(screen.getByTestId("plain-kpi").tagName).toBe("DIV");
    expect(
      screen.queryByRole("button", { name: /총자산/ }),
    ).not.toBeInTheDocument();
  });

  it("renders as an accessible selected button when onClick is provided", () => {
    const onClick = vi.fn();

    renderWithProviders(
      <KpiCard
        label="총자산"
        value="₩1.00B"
        delta="+1.00%"
        onClick={onClick}
        selected
        controlsId="kpi-evidence-panel"
        testId="button-kpi"
      />,
    );

    const button = screen.getByRole("button", { name: /총자산/ });
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("aria-controls", "kpi-evidence-panel");
    expect(button.className).toContain("ring-2");
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders the icon container when an icon is provided", () => {
    const { container } = renderWithProviders(
      <KpiCard
        label="수익률"
        value="+4.77%"
        icon={<svg data-testid="kpi-icon" />}
        accent="green"
      />,
    );

    expect(screen.getByTestId("kpi-icon")).toBeInTheDocument();
    expect(container.querySelector('[aria-hidden="true"]')?.className).toMatch(
      /bg-emerald-100/,
    );
  });

  it("does not render the icon container without an icon", () => {
    const { container } = renderWithProviders(
      <KpiCard label="종목 수" value="23" />,
    );

    expect(
      container.querySelector('[aria-hidden="true"]'),
    ).not.toBeInTheDocument();
  });

  it("maps accent props to their expected background classes", () => {
    const cases: Array<{
      accent: "blue" | "amber" | "rose" | "violet" | "slate";
      expectSubstring: string;
    }> = [
      { accent: "blue", expectSubstring: "blue" },
      { accent: "amber", expectSubstring: "amber" },
      { accent: "rose", expectSubstring: "rose" },
      { accent: "violet", expectSubstring: "primary" },
      { accent: "slate", expectSubstring: "slate" },
    ];

    for (const { accent, expectSubstring } of cases) {
      const { container } = renderWithProviders(
        <KpiCard
          label="x"
          value="y"
          icon={<span data-testid={`i-${accent}`} />}
          accent={accent}
        />,
      );

      expect(container.querySelector('[aria-hidden="true"]')?.className).toContain(
        expectSubstring,
      );
    }
  });

  it("applies positive and negative delta value colors", () => {
    const { container, rerender } = renderWithProviders(
      <KpiCard label="일일" value="₩373K" delta="+2.04%" deltaValue={2.04} />,
    );

    expect(container.querySelector("span.shrink-0.text-xs")?.className).toMatch(
      /green/,
    );

    rerender(
      <KpiCard label="일일" value="-₩500" delta="-0.03%" deltaValue={-0.03} />,
    );

    expect(container.querySelector("span.shrink-0.text-xs")?.className).toMatch(
      /red/,
    );
  });

  it("uses safe text handling classes for delta text", () => {
    renderWithProviders(
      <KpiCard label="delta" value="value" delta="+1234567890.00%" />,
    );

    expect(screen.getByText("+1234567890.00%").className).toEqual(
      expect.stringContaining("min-w-0"),
    );
    expect(screen.getByText("+1234567890.00%").className).toEqual(
      expect.stringContaining("overflow-hidden"),
    );
    expect(screen.getByText("+1234567890.00%").className).toEqual(
      expect.stringContaining("text-ellipsis"),
    );
    expect(screen.getByText("+1234567890.00%").className).toEqual(
      expect.stringContaining("break-keep"),
    );
  });
});
