import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { AssetBadge } from "./asset-badge";

describe("AssetBadge", () => {
  it("stock 자산군은 '주식' 레이블을 렌더한다 (ko 기본)", () => {
    renderWithProviders(<AssetBadge assetClass="stock" />);
    expect(screen.getByText("주식")).toBeInTheDocument();
  });

  it("crypto 자산군은 '암호화폐' 레이블을 렌더한다 (ko)", () => {
    renderWithProviders(<AssetBadge assetClass="crypto" />);
    expect(screen.getByText("암호화폐")).toBeInTheDocument();
  });

  it("fx 자산군은 'FX'/'외환' 레이블을 렌더한다", () => {
    renderWithProviders(<AssetBadge assetClass="fx" />);
    expect(screen.getByText(/FX|외환/)).toBeInTheDocument();
  });

  it("macro 자산군은 '매크로' 레이블을 렌더한다 (ko)", () => {
    renderWithProviders(<AssetBadge assetClass="macro" />);
    expect(screen.getByText("매크로")).toBeInTheDocument();
  });

  it("알 수 없는 자산군은 대문자로 폴백한다", () => {
    renderWithProviders(<AssetBadge assetClass="etf" />);
    expect(screen.getByText("ETF")).toBeInTheDocument();
  });

  it("aria-label 에 자산군 이름이 포함된다", () => {
    renderWithProviders(<AssetBadge assetClass="stock" />);
    expect(screen.getByLabelText(/자산군: 주식|Asset class: Stock/)).toBeInTheDocument();
  });

  it("className prop 을 추가로 적용한다", () => {
    const { container } = renderWithProviders(
      <AssetBadge assetClass="crypto" className="test-class" />,
    );
    expect(container.firstChild).toHaveClass("test-class");
  });
});
