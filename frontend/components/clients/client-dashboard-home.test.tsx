import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { ClientDashboardHome } from "./client-dashboard-home";

const mocks = vi.hoisted(() => ({
  getPortfolioClients: vi.fn(),
}));

vi.mock("@/lib/api/portfolio", () => ({
  getPortfolioClients: mocks.getPortfolioClients,
}));

vi.mock("@/components/dashboard/dashboard-home", () => ({
  SelectedClientDashboard: ({
    clientId,
    clientName,
  }: {
    clientId: string;
    clientName?: string;
  }) => (
    <div data-testid="mock-selected-dashboard">
      선택 대시보드 {clientName} {clientId}
    </div>
  ),
}));

const CLIENTS_RESPONSE = {
  user_id: "pb-demo",
  aum_krw: "135000000.00",
  client_count: 2,
  clients: [
    {
      client_id: "client-001",
      client_name: "고객 A",
      aum_krw: "90000000.00",
      holdings_count: 3,
      risk_grade: "medium",
      risk_score_pct: "42.00",
      total_pnl_pct: "12.50",
    },
    {
      client_id: "client-002",
      client_name: "고객 B",
      aum_krw: "45000000.00",
      holdings_count: 2,
      risk_grade: "low",
      risk_score_pct: "18.00",
      total_pnl_pct: "-1.40",
    },
  ],
};

describe("ClientDashboardHome", () => {
  beforeEach(() => {
    mocks.getPortfolioClients.mockReset();
    mocks.getPortfolioClients.mockResolvedValue(CLIENTS_RESPONSE);
  });

  it("renders client book summary and selected client dashboard", async () => {
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    expect(await screen.findByTestId("client-dashboard-home")).toBeInTheDocument();
    expect(screen.getByTestId("client-book-total-aum")).toBeInTheDocument();
    expect(screen.getByTestId("client-card-client-001")).toBeInTheDocument();
    expect(screen.getByTestId("client-card-client-002")).toBeInTheDocument();
    expect(screen.getByTestId("mock-selected-dashboard")).toHaveTextContent(
      "고객 A client-001",
    );
  });

  it("selects another client without navigating and keeps workspace link explicit", async () => {
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    await screen.findByTestId("client-dashboard-home");
    fireEvent.click(screen.getByTestId("client-select-client-002"));

    expect(screen.getByTestId("mock-selected-dashboard")).toHaveTextContent(
      "고객 B client-002",
    );
    expect(screen.getByTestId("selected-client-workspace-link")).toHaveAttribute(
      "href",
      "/clients/client-002",
    );
    expect(screen.getByTestId("client-workspace-link-client-002")).toHaveAttribute(
      "href",
      "/clients/client-002",
    );
  });
});
