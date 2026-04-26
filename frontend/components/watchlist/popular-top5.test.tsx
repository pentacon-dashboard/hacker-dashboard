import { describe, it, expect } from "vitest";
import { renderWithLocale as render, screen } from "@/lib/test-utils";
import { PopularTop5, type TopListItem } from "./popular-top5";

const MOCK_ITEMS: TopListItem[] = [
  { rank: 1, ticker: "KRW-BTC", name: "비트코인", change_pct: "11.21" },
  { rank: 2, ticker: "NVDA", name: "NVIDIA", change_pct: "3.12" },
  { rank: 3, ticker: "AAPL", name: "Apple", change_pct: "-0.50" },
];

describe("PopularTop5", () => {
  it("항목 3개를 렌더한다", () => {
    render(<PopularTop5 items={MOCK_ITEMS} />);
    expect(screen.getByTestId("popular-top5")).toBeInTheDocument();
    expect(screen.getByTestId("popular-item-KRW-BTC")).toBeInTheDocument();
    expect(screen.getByTestId("popular-item-NVDA")).toBeInTheDocument();
    expect(screen.getByTestId("popular-item-AAPL")).toBeInTheDocument();
  });

  it("빈 배열이면 empty state를 렌더한다", () => {
    render(<PopularTop5 items={[]} />);
    expect(screen.getByTestId("popular-top5-empty")).toBeInTheDocument();
  });

  it("양수 change_pct는 + 기호로 표시된다", () => {
    render(<PopularTop5 items={[MOCK_ITEMS[0]!]} />);
    expect(screen.getByText("+11.21%")).toBeInTheDocument();
  });

  it("음수 change_pct는 - 기호로 표시된다", () => {
    render(<PopularTop5 items={[MOCK_ITEMS[2]!]} />);
    expect(screen.getByText("-0.50%")).toBeInTheDocument();
  });

  it("title prop이 표시된다", () => {
    render(<PopularTop5 items={MOCK_ITEMS} title="커스텀 제목" />);
    expect(screen.getByText("커스텀 제목")).toBeInTheDocument();
  });
});
