import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { SystemInfo } from "./system-info";

const portfolioMocks = vi.hoisted(() => ({
  resetPortfolioCustomerData: vi.fn(),
}));

vi.mock("@/lib/api/portfolio", () => ({
  resetPortfolioCustomerData: portfolioMocks.resetPortfolioCustomerData,
}));

describe("SystemInfo", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    portfolioMocks.resetPortfolioCustomerData.mockReset();
    portfolioMocks.resetPortfolioCustomerData.mockResolvedValue({
      status: "cleared",
      deleted_holdings: 2,
      deleted_snapshots: 1,
      deleted_import_rows: 1,
      deleted_import_batches: 1,
      deleted_clients: 1,
      deleted_client_aliases: 1,
      deleted_watchlist_alerts: 1,
    });
  });

  it("clears browser cache without deleting customer ledger data", () => {
    localStorage.setItem("portfolio-cache", "stale");
    localStorage.setItem("hd-locale", "ko");
    sessionStorage.setItem("upload-draft", "stale");

    renderWithProviders(<SystemInfo />, { withQuery: true });

    fireEvent.click(screen.getByTestId("clear-cache-btn"));

    expect(localStorage.getItem("portfolio-cache")).toBeNull();
    expect(localStorage.getItem("hd-locale")).toBe("ko");
    expect(sessionStorage.getItem("upload-draft")).toBeNull();
    expect(portfolioMocks.resetPortfolioCustomerData).not.toHaveBeenCalled();
  });

  it("requires explicit confirmation before resetting customer data", async () => {
    renderWithProviders(<SystemInfo />, { withQuery: true });

    const button = screen.getByTestId("reset-customer-data-btn");
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByTestId("reset-customer-data-confirmation"), {
      target: { value: "CLEAR_CUSTOMER_DATA" },
    });
    fireEvent.click(button);

    await waitFor(() => {
      expect(portfolioMocks.resetPortfolioCustomerData).toHaveBeenCalledWith(
        "CLEAR_CUSTOMER_DATA",
      );
    });
    expect(await screen.findByTestId("reset-customer-data-result")).toHaveTextContent(
      "2",
    );
  });
});
