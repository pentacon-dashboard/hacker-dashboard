import type { components } from "@shared/types/api";
import { apiFetch } from "@/lib/api/client";
import { getPortfolioClients } from "@/lib/api/portfolio";

const CLIENT_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;

type UploadImportResponse = components["schemas"]["UploadImportResponse"];
type UploadImportRow = components["schemas"]["UploadImportRow"];
export type UploadImportStatus = UploadImportResponse["status"];
export type ConfirmedCsvMappingMap = NonNullable<
  components["schemas"]["UploadImportRequest"]["confirmed_mapping"]
>;
export type CsvMappingCandidateGroup =
  components["schemas"]["CsvMappingCandidateGroup"];
export type UploadBlockingError = components["schemas"]["UploadErrorDetail"];
export type UploadImportClientMode = "new" | "existing";

export interface UploadImportClientSelection {
  mode: UploadImportClientMode;
  clientId?: string;
  existingClientIds?: string[];
}

export interface UploadedClientImportResult {
  clientId: string;
  status: UploadImportStatus;
  importedRows: number;
  skippedRows: number;
  rowCounts: {
    imported: number;
    review: number;
    quarantine: number;
    garbage: number;
  };
  warnings: string[];
  mappingCandidates: CsvMappingCandidateGroup[];
  normalizedPreview: Record<string, unknown>[];
  blockingErrors: UploadBlockingError[];
  importBatchKey?: string | null;
}

function sanitizeClientId(value: string | undefined): string | null {
  const candidate = value?.trim();
  if (!candidate) return null;
  return CLIENT_ID_PATTERN.test(candidate) ? candidate : null;
}

export function getNextPortfolioClientId(existingClientIds: string[]): string {
  const maxNumericId = existingClientIds.reduce((max, clientId) => {
    const match = /^client-(\d+)$/i.exec(clientId);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);

  const next = Math.max(maxNumericId + 1, 1);
  return `client-${String(next).padStart(3, "0")}`;
}

async function getFallbackClientId(): Promise<string> {
  try {
    const clients = await getPortfolioClients();
    return getNextPortfolioClientId(clients.clients.map((client) => client.client_id));
  } catch {
    return "client-001";
  }
}

async function resolveRequestedClientId(
  selection?: UploadImportClientSelection,
): Promise<string> {
  if (!selection) return getFallbackClientId();

  const selectedClientId = sanitizeClientId(selection.clientId);
  if (selection.mode === "existing") {
    if (!selectedClientId) {
      throw new Error("기존 고객을 선택해 주세요.");
    }
    if (
      selection.existingClientIds &&
      !selection.existingClientIds.includes(selectedClientId)
    ) {
      throw new Error("선택한 기존 고객을 찾을 수 없습니다.");
    }
    return selectedClientId;
  }

  if (selectedClientId) return selectedClientId;
  if (selection.existingClientIds) {
    return getNextPortfolioClientId(selection.existingClientIds);
  }
  return getFallbackClientId();
}

function resolveImportedClientId(
  response: UploadImportResponse,
  fallbackClientId: string,
): string {
  const responseClientId = sanitizeClientId(response.client_id);
  if (responseClientId) return responseClientId;

  const importedHoldingClientId = response.holdings
    ?.map((holding) => sanitizeClientId(holding.client_id))
    .find((clientId): clientId is string => Boolean(clientId));
  return importedHoldingClientId ?? fallbackClientId;
}

function safeRowCount(rows: UploadImportRow[] | undefined): number {
  return Array.isArray(rows) ? rows.length : 0;
}

function hasRowLedger(response: UploadImportResponse): boolean {
  return [
    response.imported_rows,
    response.recoverable_rows,
    response.quarantined_rows,
    response.garbage_rows,
  ].some(Array.isArray);
}

function getRowCounts(response: UploadImportResponse): UploadedClientImportResult["rowCounts"] {
  return {
    imported: Array.isArray(response.imported_rows)
      ? response.imported_rows.length
      : response.imported_count,
    review: safeRowCount(response.recoverable_rows),
    quarantine: safeRowCount(response.quarantined_rows),
    garbage: safeRowCount(response.garbage_rows),
  };
}

export async function importPortfolioCsvAsClient(
  uploadId: string,
  selection?: UploadImportClientSelection,
  confirmedMapping?: ConfirmedCsvMappingMap,
): Promise<UploadedClientImportResult> {
  const requestedClientId = await resolveRequestedClientId(selection);
  const response = await apiFetch<UploadImportResponse>("/upload/import", {
    method: "POST",
    body: JSON.stringify({
      upload_id: uploadId,
      client_id: requestedClientId,
      ...(confirmedMapping ? { confirmed_mapping: confirmedMapping } : {}),
    }),
  });

  const normalizedCount = response.normalized_holdings?.length ?? response.imported_count;
  const rowCounts = getRowCounts(response);
  const skippedRows = hasRowLedger(response)
    ? rowCounts.review + rowCounts.quarantine + rowCounts.garbage
    : Math.max(normalizedCount - response.imported_count, 0);
  return {
    clientId: resolveImportedClientId(response, requestedClientId),
    status: response.status,
    importedRows: response.imported_count,
    skippedRows,
    rowCounts,
    warnings: response.normalization_warnings ?? [],
    mappingCandidates: response.mapping_candidates ?? [],
    normalizedPreview: response.normalized_preview ?? [],
    blockingErrors: response.blocking_errors ?? [],
    importBatchKey: response.import_batch_key,
  };
}
