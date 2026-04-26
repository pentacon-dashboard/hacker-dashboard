import { describe, it, expect } from "vitest";
import { renderWithLocale as render, screen } from "@/lib/test-utils";
import { AllocationBreakdown, type AllocationSlice } from "./allocation-breakdown";

const SAMPLE: AllocationSlice[] = [
  { key: "stock_us", name: "해외 주식", ratio: 0.432, value_krw: 8_100_720, color: "#6366f1" },
  { key: "stock_kr", name: "국내 주식", ratio: 0.218, value_krw: 4_089_680, color: "#22c55e" },
  { key: "crypto", name: "암호화폐", ratio: 0.188, value_krw: 3_526_880, color: "#f59e0b" },
];

describe("AllocationBreakdown", () => {
  it("데이터가 없으면 empty 상태 메시지를 표시한다", () => {
    render(<AllocationBreakdown data={[]} />);
    expect(screen.getByText("보유 자산 없음")).toBeInTheDocument();
  });

  it("모든 슬라이스의 라벨을 렌더한다", () => {
    render(<AllocationBreakdown data={SAMPLE} />);
    expect(screen.getByText("해외 주식")).toBeInTheDocument();
    expect(screen.getByText("국내 주식")).toBeInTheDocument();
    expect(screen.getByText("암호화폐")).toBeInTheDocument();
  });

  it("각 슬라이스의 비중을 소수점 1자리 % 로 표시한다", () => {
    render(<AllocationBreakdown data={SAMPLE} />);
    expect(screen.getByText("43.2%")).toBeInTheDocument();
    expect(screen.getByText("21.8%")).toBeInTheDocument();
    expect(screen.getByText("18.8%")).toBeInTheDocument();
  });

  it("각 슬라이스의 금액을 compact 포맷으로 표시한다", () => {
    render(<AllocationBreakdown data={SAMPLE} />);
    // formatKRWCompact(8_100_720) = ₩8.10M
    expect(screen.getByText("₩8.10M")).toBeInTheDocument();
    expect(screen.getByText("₩4.09M")).toBeInTheDocument();
    expect(screen.getByText("₩3.53M")).toBeInTheDocument();
  });

  it("컬러 도트를 각 항목마다 하나씩 렌더한다", () => {
    const { container } = render(<AllocationBreakdown data={SAMPLE} />);
    const dots = container.querySelectorAll('[aria-hidden="true"]');
    expect(dots.length).toBeGreaterThanOrEqual(SAMPLE.length);
  });
});
