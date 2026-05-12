import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { getAiInsight, getPortfolioSummary } from "@/lib/api/portfolio";
import { ReferencePanel } from "./reference-panel";

vi.mock("@/lib/api/portfolio", () => ({
  getAiInsight: vi.fn(),
  getPortfolioSummary: vi.fn(),
}));

const mockGetAiInsight = vi.mocked(getAiInsight);
const mockGetPortfolioSummary = vi.mocked(getPortfolioSummary);

const summary = {
  user_id: "pb-demo",
  client_id: "client-001",
  client_name: "고객 A",
  total_value_krw: "100000000",
  total_cost_krw: null,
  total_pnl_krw: null,
  total_pnl_pct: null,
  daily_change_krw: "120000",
  daily_change_pct: "0.12",
  asset_class_breakdown: {},
  sector_breakdown: {},
  holdings: [],
  holdings_count: 0,
  worst_asset_pct: null,
  risk_score_pct: "0",
  period_change_pct: "0",
  period_days: 30,
  dimension_breakdown: [],
  win_rate_pct: null,
  market_leaders: [],
};

describe("ReferencePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetAiInsight.mockResolvedValue({
      summary: "Deterministic insight",
      bullets: [],
      generated_at: "2026-05-13T00:00:00Z",
      stub_mode: true,
      gates: {},
    });
  });

  it("renders missing aggregate PnL as unknown instead of NaN", async () => {
    mockGetPortfolioSummary.mockResolvedValue(summary);

    renderWithProviders(<ReferencePanel />);

    const pnl = await screen.findByTestId("summary-pnl-pct");
    expect(pnl).toHaveTextContent("-");
    expect(pnl).not.toHaveTextContent("NaN");
    expect(screen.queryByText(/NaN%/)).not.toBeInTheDocument();
  });
});
