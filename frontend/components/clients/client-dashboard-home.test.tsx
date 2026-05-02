import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { ClientDashboardHome } from "./client-dashboard-home";

const navMocks = vi.hoisted(() => ({
  search: "",
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navMocks.replace }),
  useSearchParams: () => new URLSearchParams(navMocks.search),
}));

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
      <a
        data-testid="selected-client-workspace-link"
        href={`/clients/${clientId}`}
      >
        워크스페이스 열기
      </a>
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
    navMocks.search = "";
    navMocks.replace.mockReset();
    mocks.getPortfolioClients.mockReset();
    mocks.getPortfolioClients.mockResolvedValue(CLIENTS_RESPONSE);
  });

  it("renders image-style client book summary with first client selected by default", async () => {
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    expect(await screen.findByTestId("client-dashboard-home")).toBeInTheDocument();
    expect(screen.getByTestId("client-book-total-aum")).toBeInTheDocument();
    expect(screen.getByTestId("client-select-client-001")).toBeInTheDocument();
    expect(screen.getByTestId("client-select-client-002")).toBeInTheDocument();
    expect(screen.getByTestId("client-search-input")).toBeInTheDocument();
    expect(screen.getByTestId("new-client-upload-link")).toHaveAttribute(
      "href",
      "/upload",
    );
    expect(screen.getByTestId("mock-selected-dashboard")).toHaveTextContent(
      "고객 A client-001",
    );
  });

  it("selects another client in-place and updates the URL query", async () => {
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    await screen.findByTestId("client-dashboard-home");
    fireEvent.click(screen.getByTestId("client-select-client-002"));

    expect(screen.getByTestId("mock-selected-dashboard")).toHaveTextContent(
      "고객 B client-002",
    );
    expect(navMocks.replace).toHaveBeenCalledWith("/?client=client-002", {
      scroll: false,
    });
    expect(screen.getByTestId("selected-client-workspace-link")).toHaveAttribute(
      "href",
      "/clients/client-002",
    );
  });

  it("uses the client query parameter when present", async () => {
    navMocks.search = "client=client-002";
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    await screen.findByTestId("client-dashboard-home");

    expect(screen.getByTestId("mock-selected-dashboard")).toHaveTextContent(
      "고객 B client-002",
    );
  });

  it("filters clients locally by name or id", async () => {
    renderWithProviders(<ClientDashboardHome />, { withQuery: true });

    await screen.findByTestId("client-dashboard-home");
    fireEvent.change(screen.getByTestId("client-search-input"), {
      target: { value: "client-002" },
    });

    expect(screen.queryByTestId("client-select-client-001")).not.toBeInTheDocument();
    expect(screen.getByTestId("client-select-client-002")).toBeInTheDocument();
  });
});
