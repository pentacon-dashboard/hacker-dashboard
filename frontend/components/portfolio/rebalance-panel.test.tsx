import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { RebalancePanel } from "./rebalance-panel";
import * as rebalanceApi from "@/lib/api/rebalance";
import type { RebalanceResponse } from "@/lib/api/rebalance";

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

function makeRebalanceResponse(overrides: Partial<RebalanceResponse> = {}): RebalanceResponse {
  return {
    request_id: "test-uuid-1234",
    status: "ok",
    current_allocation: { stock_kr: 0.07, stock_us: 0.19, crypto: 0.74, cash: 0 },
    target_allocation: { stock_kr: 0.2, stock_us: 0.4, crypto: 0.3, cash: 0.1 },
    drift: { stock_kr: -0.13, stock_us: -0.21, crypto: 0.44, cash: -0.1 },
    actions: [
      {
        action: "sell",
        market: "upbit",
        code: "KRW-BTC",
        asset_class: "crypto",
        quantity: "0.02",
        estimated_value_krw: "1700000",
        reason: "crypto 비중 74% → 목표 30%",
      },
      {
        action: "buy",
        market: "yahoo",
        code: "AAPL",
        asset_class: "stock_us",
        quantity: "3",
        estimated_value_krw: "850000",
        reason: "stock_us 목표까지 +21% 부족",
      },
    ],
    expected_allocation: { stock_kr: 0.2, stock_us: 0.4, crypto: 0.3, cash: 0.1 },
    summary: {
      total_trades: 2,
      total_sell_value_krw: "1700000",
      total_buy_value_krw: "850000",
      rebalance_cost_estimate_krw: "5000",
    },
    llm_analysis: {
      headline: "코인 비중 과도 — 매도 후 주식 보강 권장",
      narrative: "현재 포트폴리오는 crypto에 74% 집중되어 있어 리스크가 높습니다.",
      warnings: ["BTC 매도 시 국내 과세 구간 주의"],
      confidence: 0.82,
    },
    meta: {
      latency_ms: 2400,
      gates: { schema_gate: "pass", domain_gate: "pass", critique_gate: "pass" },
      evidence_snippets: [],
    },
    ...overrides,
  };
}

describe("RebalancePanel", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.restoreAllMocks();
  });

  it("기본 균형형 프리셋(합계 100%)일 때 '제안 받기' 버튼이 활성화됨", () => {
    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    expect(button).not.toBeDisabled();
  });

  it("슬라이더 하나를 변경하면 나머지 비중을 자동 보정해 합계 100%를 유지함", () => {
    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    // 초기 균형형: 20+40+30+10=100 → 활성화
    expect(button).not.toBeDisabled();

    const sliders = screen.getAllByRole("slider");
    fireEvent.change(sliders[0]!, { target: { value: "50" } });

    const values = sliders.map((slider) => Number((slider as HTMLInputElement).value));
    expect(values).toEqual([50, 25, 19, 6]);
    expect(values.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(button).not.toBeDisabled();
  });

  it("합계가 100%일 때 '제안 받기' 버튼이 활성화됨", () => {
    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    expect(button).not.toBeDisabled();
  });

  it("프리셋 버튼 클릭 시 합계가 100%가 됨", () => {
    render(<RebalancePanel />);
    const balancedBtn = screen.getByRole("button", { name: "균형형" });
    fireEvent.click(balancedBtn);
    expect(screen.getByText(/합계 100\.0%/)).toBeInTheDocument();
  });

  it("공격형 프리셋 버튼 클릭 시 합계가 100%이고 버튼이 활성화됨", () => {
    render(<RebalancePanel />);
    const aggressiveBtn = screen.getByRole("button", { name: "공격형 70/30" });
    fireEvent.click(aggressiveBtn);
    expect(screen.getByText(/합계 100\.0%/)).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "제안 받기" });
    expect(button).not.toBeDisabled();
  });

  it("API 호출 성공 시 결과가 렌더됨", async () => {
    const mockResponse = makeRebalanceResponse();
    vi.spyOn(rebalanceApi, "requestRebalance").mockResolvedValueOnce(mockResponse);

    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByText("코인 비중 과도 — 매도 후 주식 보강 권장")).toBeInTheDocument();
    });
  });

  it("API 호출 실패 시 에러 배너가 렌더됨", async () => {
    vi.spyOn(rebalanceApi, "requestRebalance").mockRejectedValueOnce(
      new Error("Rebalance API 500: Internal Server Error"),
    );

    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByText(/Rebalance API 500/)).toBeInTheDocument();
    });
  });

  it("llm_analysis=null & status=degraded 응답 시 degraded 배너가 렌더됨", async () => {
    const degradedResponse = makeRebalanceResponse({
      llm_analysis: null,
      status: "degraded",
    });
    vi.spyOn(rebalanceApi, "requestRebalance").mockResolvedValueOnce(degradedResponse);

    render(<RebalancePanel />);
    const button = screen.getByRole("button", { name: "제안 받기" });
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getAllByText(/LLM 해석 실패/).length).toBeGreaterThan(0);
      expect(screen.getByText(/계산된 액션은 유효합니다/)).toBeInTheDocument();
    });
  });
});
