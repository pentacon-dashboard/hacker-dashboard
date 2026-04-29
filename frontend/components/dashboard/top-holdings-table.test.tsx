import { describe, it, expect } from "vitest";
import { renderWithLocale as render, screen, within } from "@/lib/test-utils";
import { TopHoldingsTable } from "./top-holdings-table";
import type { HoldingDetail } from "@/lib/api/portfolio";

function holding(overrides: Partial<HoldingDetail>): HoldingDetail {
  return {
    id: 1,
    market: "yahoo",
    code: "AAPL",
    quantity: "1.00000000",
    avg_cost: "100.0000",
    currency: "USD",
    current_price: "120.0000",
    current_price_krw: "160000.00",
    value_krw: "1000000.00",
    cost_krw: "900000.00",
    pnl_krw: "100000.00",
    pnl_pct: "10.00",
    ...overrides,
  };
}

const SAMPLE: HoldingDetail[] = [
  holding({ id: 1, code: "AAPL", value_krw: "3474000.00", pnl_pct: "16.50" }),
  holding({ id: 2, code: "NVDA", value_krw: "4182000.00", pnl_pct: "22.15" }),
  holding({ id: 3, code: "005930.KS", market: "naver_kr", value_krw: "2968000.00", pnl_pct: "4.51" }),
  holding({ id: 4, code: "KRW-BTC", market: "upbit", value_krw: "3082800.00", pnl_pct: "11.21" }),
  holding({ id: 5, code: "KRW-ETH", market: "upbit", value_krw: "1818000.00", pnl_pct: "-3.85" }),
  holding({ id: 6, code: "TSLA", value_krw: "2324000.00", pnl_pct: "9.52" }),
];

describe("TopHoldingsTable", () => {
  it("빈 데이터면 empty 메시지를 표시한다", () => {
    render(<TopHoldingsTable holdings={[]} />);
    expect(screen.getByText("보유 자산 없음")).toBeInTheDocument();
  });

  it("6개 컬럼 헤더를 렌더한다", () => {
    render(<TopHoldingsTable holdings={SAMPLE} />);
    const headers = screen.getAllByRole("columnheader");
    const texts = headers.map((h) => h.textContent);
    expect(texts).toEqual(["#", "종목", "시장", "평가액", "수익률", "비중"]);
  });

  it("value_krw 내림차순으로 상위 5개만 표시한다 (default limit=5)", () => {
    render(<TopHoldingsTable holdings={SAMPLE} />);
    const rows = screen.getAllByRole("row").slice(1); // header 제외
    expect(rows).toHaveLength(5);
    // 1위는 NVDA (4.18M)
    expect(within(rows[0]!).getByText("NVIDIA")).toBeInTheDocument();
    // 2위는 AAPL (3.47M)
    expect(within(rows[1]!).getByText("Apple")).toBeInTheDocument();
  });

  it("totalValueKrw 미제공 시 holdings 합으로 비중을 계산한다", () => {
    const twoItems: HoldingDetail[] = [
      holding({ id: 10, code: "A", value_krw: "1000000.00" }),
      holding({ id: 11, code: "B", value_krw: "3000000.00" }),
    ];
    render(<TopHoldingsTable holdings={twoItems} />);
    // 전체 4M 중 A=25%, B=75%
    expect(screen.getByText("25.0%")).toBeInTheDocument();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
  });

  it("totalValueKrw 가 주어지면 해당 값으로 비중을 계산한다", () => {
    const items: HoldingDetail[] = [
      holding({ id: 20, code: "A", value_krw: "500000.00" }),
    ];
    // total=1M → A=50%
    render(<TopHoldingsTable holdings={items} totalValueKrw={1_000_000} />);
    expect(screen.getByText("50.0%")).toBeInTheDocument();
  });

  it("수익률에 부호(+/-)를 붙여 표시한다", () => {
    render(<TopHoldingsTable holdings={SAMPLE} />);
    expect(screen.getByText("+22.15%")).toBeInTheDocument();
    // 음수 종목은 limit=5 로 잘려나갈 수 있음 — limit=6 으로 확인
    const { unmount } = render(
      <TopHoldingsTable holdings={SAMPLE} limit={6} />,
    );
    expect(screen.getAllByText("-3.85%").length).toBeGreaterThan(0);
    unmount();
  });
});
