import { fireEvent, screen, waitFor } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import UploadPage from "./page";

const navMocks = vi.hoisted(() => ({
  push: vi.fn(),
}));

const portfolioApi = vi.hoisted(() => ({
  getPortfolioClients: vi.fn(),
}));

const uploadImport = vi.hoisted(() => ({
  importPortfolioCsvAsClient: vi.fn(),
  getNextPortfolioClientId: vi.fn((existingClientIds: string[]) => {
    const max = existingClientIds.reduce((current, clientId) => {
      const match = /^client-(\d+)$/i.exec(clientId);
      return match ? Math.max(current, Number(match[1])) : current;
    }, 0);
    return `client-${String(max + 1).padStart(3, "0")}`;
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: navMocks.push }),
}));

vi.mock("@/lib/api/portfolio", () => ({
  getPortfolioClients: portfolioApi.getPortfolioClients,
}));

vi.mock("@/lib/portfolio/upload-import", () => ({
  getNextPortfolioClientId: uploadImport.getNextPortfolioClientId,
  importPortfolioCsvAsClient: uploadImport.importPortfolioCsvAsClient,
}));

vi.mock("@/components/upload/dropzone-card", () => ({
  DropzoneCard: ({
    onFileAccepted,
    uploading,
  }: {
    onFileAccepted: (file: File) => void;
    uploading?: boolean;
  }) => (
    <button
      type="button"
      data-testid="mock-file-upload"
      disabled={uploading}
      onClick={() =>
        onFileAccepted(new File(["code,quantity\nAAPL,1"], "positions.csv", { type: "text/csv" }))
      }
    >
      Upload
    </button>
  ),
}));

vi.mock("@/components/upload/validation-card", () => ({
  ValidationCard: ({ error }: { error?: string | null }) => (
    <div data-testid="mock-validation-card">{error}</div>
  ),
}));

vi.mock("@/components/upload/preview-table", () => ({
  PreviewTable: () => <div data-testid="mock-preview-table" />,
}));

vi.mock("@/components/upload/analyzer-config-card", () => ({
  AnalyzerConfigCard: () => <div data-testid="mock-analyzer-config" />,
}));

vi.mock("@/components/upload/analyze-progress-card", () => ({
  AnalyzeProgressCard: ({
    disabled,
    onComplete,
  }: {
    disabled?: boolean;
    onComplete?: () => void | Promise<void>;
  }) => (
    <button
      type="button"
      data-testid="mock-analyze"
      disabled={disabled}
      onClick={() => void onComplete?.()}
    >
      Analyze
    </button>
  ),
}));

vi.mock("@/components/upload/csv-template-card", () => ({
  CsvTemplateCard: () => <div data-testid="mock-csv-template" />,
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

const UPLOAD_RESPONSE = {
  upload_id: "upload-123",
  total_rows: 1,
  valid_rows: 1,
  error_rows: 0,
  warning_rows: 0,
  preview: [{ code: "AAPL", quantity: "1" }],
  schema_fingerprint: "abcdef12",
  created_at: "2026-05-02T00:00:00Z",
};

describe("UploadPage multi-client import flow", () => {
  let invalidateSpy: MockInstance<QueryClient["invalidateQueries"]>;

  beforeEach(() => {
    navMocks.push.mockReset();
    portfolioApi.getPortfolioClients.mockReset();
    uploadImport.importPortfolioCsvAsClient.mockReset();
    uploadImport.getNextPortfolioClientId.mockClear();
    portfolioApi.getPortfolioClients.mockResolvedValue(CLIENTS_RESPONSE);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => UPLOAD_RESPONSE,
      }),
    );
    invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");
  });

  afterEach(() => {
    invalidateSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("imports a valid CSV into the generated new client and opens that workspace", async () => {
    uploadImport.importPortfolioCsvAsClient.mockResolvedValue({
      clientId: "client-003",
      status: "imported",
      importedRows: 1,
      skippedRows: 0,
      warnings: [],
    });

    renderWithProviders(<UploadPage />, { withQuery: true });

    await waitFor(() =>
      expect(screen.getByTestId("upload-new-client-id")).toHaveTextContent("client-003"),
    );

    fireEvent.click(screen.getByTestId("mock-file-upload"));

    await waitFor(() =>
      expect(uploadImport.importPortfolioCsvAsClient).toHaveBeenCalledWith(
        "upload-123",
        {
          mode: "new",
          clientId: "client-003",
          existingClientIds: ["client-001", "client-002"],
        },
      ),
    );
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["portfolio", "clients"],
      }),
    );

    await waitFor(() => expect(screen.getByTestId("mock-analyze")).not.toBeDisabled());
    fireEvent.click(screen.getByTestId("mock-analyze"));

    expect(navMocks.push).toHaveBeenCalledWith("/clients/client-003");
  });

  it("imports a valid CSV into the selected existing client", async () => {
    uploadImport.importPortfolioCsvAsClient.mockResolvedValue({
      clientId: "client-002",
      status: "imported",
      importedRows: 1,
      skippedRows: 0,
      warnings: [],
    });

    renderWithProviders(<UploadPage />, { withQuery: true });

    await waitFor(() =>
      expect(screen.getByTestId("upload-client-mode-existing")).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByTestId("upload-client-mode-existing"));
    fireEvent.change(screen.getByTestId("upload-existing-client-select"), {
      target: { value: "client-002" },
    });
    fireEvent.click(screen.getByTestId("mock-file-upload"));

    await waitFor(() =>
      expect(uploadImport.importPortfolioCsvAsClient).toHaveBeenCalledWith(
        "upload-123",
        {
          mode: "existing",
          clientId: "client-002",
          existingClientIds: ["client-001", "client-002"],
        },
      ),
    );

    await waitFor(() => expect(screen.getByTestId("mock-analyze")).not.toBeDisabled());
    fireEvent.click(screen.getByTestId("mock-analyze"));

    expect(navMocks.push).toHaveBeenCalledWith("/clients/client-002");
  });
});
