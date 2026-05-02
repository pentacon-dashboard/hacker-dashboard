import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getNextPortfolioClientId,
  importPortfolioCsvAsClient,
} from "./upload-import";

const apiClient = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}));

const portfolioApi = vi.hoisted(() => ({
  getPortfolioClients: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiFetch: apiClient.apiFetch,
}));

vi.mock("@/lib/api/portfolio", () => ({
  getPortfolioClients: portfolioApi.getPortfolioClients,
}));

describe("upload-import", () => {
  beforeEach(() => {
    apiClient.apiFetch.mockReset();
    portfolioApi.getPortfolioClients.mockReset();
    portfolioApi.getPortfolioClients.mockResolvedValue({
      clients: [{ client_id: "client-001" }, { client_id: "client-002" }],
    });
  });

  it("computes the next generated client id from existing numeric ids", () => {
    expect(getNextPortfolioClientId(["client-001", "client-009", "vip"])).toBe(
      "client-010",
    );
  });

  it("posts the cached upload id to the backend import endpoint with the next client id", async () => {
    apiClient.apiFetch.mockResolvedValue({
      status: "imported",
      client_id: "client-003",
      imported_count: 1,
      holdings: [
        {
          id: 10,
          user_id: "pb-demo",
          client_id: "client-003",
          client_name: "Client C",
          market: "naver_kr",
          code: "005930",
          quantity: "10.00000000",
          avg_cost: "72000.00000000",
          currency: "KRW",
          created_at: "2026-05-01T00:00:00Z",
          updated_at: "2026-05-01T00:00:00Z",
        },
      ],
      normalized_holdings: [{ code: "005930" }],
      normalization_warnings: [],
    });

    const result = await importPortfolioCsvAsClient("upload-123", {
      mode: "new",
      existingClientIds: ["client-001", "client-002"],
    });

    expect(apiClient.apiFetch).toHaveBeenCalledWith("/upload/import", {
      method: "POST",
      body: JSON.stringify({ upload_id: "upload-123", client_id: "client-003" }),
    });
    expect(result).toEqual({
      clientId: "client-003",
      status: "imported",
      importedRows: 1,
      skippedRows: 0,
      warnings: [],
    });
  });

  it("uses the selected existing client id for the import request", async () => {
    apiClient.apiFetch.mockResolvedValue({
      status: "imported",
      client_id: "client-002",
      imported_count: 1,
      holdings: [{ client_id: "client-002" }],
      normalized_holdings: [{ code: "NVDA", client_id: "client-vip" }],
      normalization_warnings: [],
    });

    const result = await importPortfolioCsvAsClient("upload-123", {
      mode: "existing",
      clientId: "client-002",
      existingClientIds: ["client-001", "client-002"],
    });

    expect(apiClient.apiFetch).toHaveBeenCalledWith("/upload/import", {
      method: "POST",
      body: JSON.stringify({ upload_id: "upload-123", client_id: "client-002" }),
    });
    expect(result.clientId).toBe("client-002");
  });

  it("falls back to fetching clients when no new-client ids are provided", async () => {
    apiClient.apiFetch.mockResolvedValue({
      status: "imported",
      client_id: "client-003",
      imported_count: 1,
      holdings: [{ client_id: "client-003" }],
      normalized_holdings: [{ code: "NVDA" }],
      normalization_warnings: [],
    });

    await importPortfolioCsvAsClient("upload-123", { mode: "new" });

    expect(portfolioApi.getPortfolioClients).toHaveBeenCalledTimes(1);
    expect(apiClient.apiFetch).toHaveBeenCalledWith("/upload/import", {
      method: "POST",
      body: JSON.stringify({ upload_id: "upload-123", client_id: "client-003" }),
    });
  });

  it("rejects an existing client selection that is not in the known client list", async () => {
    await expect(
      importPortfolioCsvAsClient("upload-123", {
        mode: "existing",
        clientId: "client-999",
        existingClientIds: ["client-001"],
      }),
    ).rejects.toThrow("선택한 기존 고객을 찾을 수 없습니다.");
    expect(apiClient.apiFetch).not.toHaveBeenCalled();
  });

  it("returns needs_confirmation without treating it as an imported client", async () => {
    apiClient.apiFetch.mockResolvedValue({
      status: "needs_confirmation",
      client_id: "client-003",
      imported_count: 0,
      holdings: [],
      normalized_holdings: [{ code: "AAPL" }],
      normalization_warnings: ["multiple candidates for symbol"],
    });

    const result = await importPortfolioCsvAsClient("upload-ambiguous", {
      mode: "new",
      existingClientIds: ["client-001", "client-002"],
    });

    expect(result).toEqual({
      clientId: "client-003",
      status: "needs_confirmation",
      importedRows: 0,
      skippedRows: 1,
      warnings: ["multiple candidates for symbol"],
    });
  });
});
