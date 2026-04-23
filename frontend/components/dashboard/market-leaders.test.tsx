import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarketLeaders, type MarketLeader } from "./market-leaders";

const MOCK_LEADERS: MarketLeader[] = [
  {
    rank: 1,
    name: "NVIDIA",
    ticker: "NVDA",
    logo_url: null,
    price_display: "$512.40",
    change_pct: "3.12",
    change_krw: null,
  },
  {
    rank: 2,
    name: "삼성전자",
    ticker: "005930",
    logo_url: null,
    price_display: "₩74,200",
    change_pct: "-1.20",
    change_krw: null,
  },
  {
    rank: 3,
    name: "Bitcoin",
    ticker: "KRW-BTC",
    logo_url: null,
    price_display: "₩73.40M",
    change_pct: "2.45",
    change_krw: "₩1.76M",
  },
];

describe("MarketLeaders", () => {
  it("3개 카드 모두 렌더한다", () => {
    render(<MarketLeaders leaders={MOCK_LEADERS} />);
    expect(screen.getByTestId("market-leaders")).toBeInTheDocument();
    expect(screen.getByTestId("market-leader-1")).toBeInTheDocument();
    expect(screen.getByTestId("market-leader-2")).toBeInTheDocument();
    expect(screen.getByTestId("market-leader-3")).toBeInTheDocument();
    expect(screen.getByText("NVIDIA")).toBeInTheDocument();
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText("Bitcoin")).toBeInTheDocument();
  });

  it("빈 배열이면 empty state를 렌더한다", () => {
    render(<MarketLeaders leaders={[]} />);
    expect(screen.getByTestId("market-leaders-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("market-leaders")).not.toBeInTheDocument();
  });

  it("logo_url null 이면 이니셜 fallback을 렌더한다 (img 없음)", () => {
    const { container } = render(<MarketLeaders leaders={[MOCK_LEADERS[0]!]} />);
    // logo_url=null → <img> 없고 이니셜 div 존재
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    // 이니셜: "NVIDIA" → 단어 1개 → "N" (첫 글자)
    const avatarDiv = container.querySelector('[aria-hidden="true"]');
    expect(avatarDiv?.textContent).toBe("N");
  });

  it("양수 변동률은 emerald 색, 음수는 red 색 클래스로 표시된다", () => {
    const { container } = render(<MarketLeaders leaders={MOCK_LEADERS} />);
    const emeraldEl = container.querySelector(".text-emerald-600, .dark\\:text-emerald-400");
    const redEl = container.querySelector(".text-red-600, .dark\\:text-red-400");
    expect(emeraldEl).toBeInTheDocument();
    expect(redEl).toBeInTheDocument();
  });

  it("change_krw 값이 있으면 환산 텍스트를 렌더한다", () => {
    render(<MarketLeaders leaders={[MOCK_LEADERS[2]!]} />);
    expect(screen.getByText("₩1.76M")).toBeInTheDocument();
  });
});
