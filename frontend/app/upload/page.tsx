"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, Loader2, UserPlus, Users } from "lucide-react";
import { DropzoneCard } from "@/components/upload/dropzone-card";
import { ValidationCard, type ValidationResult } from "@/components/upload/validation-card";
import { PreviewTable } from "@/components/upload/preview-table";
import { AnalyzerConfigCard, type AnalyzerConfig } from "@/components/upload/analyzer-config-card";
import { AnalyzeProgressCard } from "@/components/upload/analyze-progress-card";
import { CsvTemplateCard } from "@/components/upload/csv-template-card";
import { API_BASE } from "@/lib/api/client";
import { getPortfolioClients, type PortfolioClientsResponse } from "@/lib/api/portfolio";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getNextPortfolioClientId,
  importPortfolioCsvAsClient,
  type UploadImportClientMode,
  type UploadImportClientSelection,
  type UploadedClientImportResult,
} from "@/lib/portfolio/upload-import";

const DEFAULT_CONFIG: AnalyzerConfig = {
  analyzer: "portfolio",
  period_days: 90,
  currency: "KRW",
  include_fx: true,
};

function getPreviewRows(result: ValidationResult | null): Record<string, string>[] {
  return result?.preview_rows ?? result?.preview ?? [];
}

function getPreviewColumns(result: ValidationResult | null): string[] {
  const rows = getPreviewRows(result);
  return result?.columns_detected ?? Object.keys(rows[0] ?? {});
}

type ClientRow = PortfolioClientsResponse["clients"][number];

function ClientTargetPanel({
  mode,
  clients,
  selectedExistingClientId,
  generatedClientId,
  loading,
  disabled,
  onModeChange,
  onExistingClientChange,
}: {
  mode: UploadImportClientMode;
  clients: ClientRow[];
  selectedExistingClientId: string;
  generatedClientId: string;
  loading: boolean;
  disabled: boolean;
  onModeChange: (mode: UploadImportClientMode) => void;
  onExistingClientChange: (clientId: string) => void;
}) {
  const existingDisabled = disabled || loading || clients.length === 0;
  const selectedClient = clients.find(
    (client) => client.client_id === selectedExistingClientId,
  );

  return (
    <div
      className="md:col-span-2 rounded-lg border bg-card p-4"
      data-testid="upload-client-target-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">고객 선택</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            업로드한 보유자산을 새 고객 또는 기존 고객 워크스페이스에 저장합니다.
          </p>
        </div>
        <div className="flex rounded-md border bg-muted/30 p-1">
          <button
            type="button"
            onClick={() => onModeChange("new")}
            disabled={disabled}
            aria-pressed={mode === "new"}
            className={`inline-flex h-8 items-center gap-2 rounded px-3 text-xs font-semibold transition-colors ${
              mode === "new"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            data-testid="upload-client-mode-new"
          >
            <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
            새 고객
          </button>
          <button
            type="button"
            onClick={() => onModeChange("existing")}
            disabled={existingDisabled}
            aria-pressed={mode === "existing"}
            className={`inline-flex h-8 items-center gap-2 rounded px-3 text-xs font-semibold transition-colors ${
              mode === "existing"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            } disabled:cursor-not-allowed disabled:opacity-50`}
            data-testid="upload-client-mode-existing"
          >
            <Users className="h-3.5 w-3.5" aria-hidden="true" />
            기존 고객
          </button>
        </div>
      </div>

      <div className="mt-4 rounded-md border bg-muted/20 px-3 py-3">
        {mode === "new" ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground">새 고객 ID</p>
              <p className="mt-1 font-mono text-sm font-semibold" data-testid="upload-new-client-id">
                {loading ? "계산 중" : generatedClientId}
              </p>
            </div>
            <p className="max-w-md text-xs text-muted-foreground">
              기존 고객 ID를 기준으로 다음 번호를 배정합니다. CSV 안의 고객 ID는 원본 근거로 보존됩니다.
            </p>
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="upload-existing-client">
              저장할 기존 고객
            </label>
            <select
              id="upload-existing-client"
              value={selectedExistingClientId}
              onChange={(event) => onExistingClientChange(event.target.value)}
              disabled={existingDisabled}
              className="h-9 rounded-md border bg-background px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
              data-testid="upload-existing-client-select"
            >
              {clients.map((client) => (
                <option key={client.client_id} value={client.client_id}>
                  {client.client_name} ({client.client_id})
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground sm:col-span-2">
              {selectedClient
                ? `${selectedClient.client_name} 워크스페이스에 병합됩니다.`
                : "기존 고객 목록을 불러온 뒤 선택할 수 있습니다."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ImportStatusPanel({
  result,
  importing,
}: {
  result: UploadedClientImportResult | null;
  importing: boolean;
}) {
  if (!importing && !result) return null;

  if (importing) {
    return (
      <div
        className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-xs text-primary"
        data-testid="upload-import-status"
      >
        <Loader2 className="h-4 w-4 shrink-0 animate-spin" aria-hidden="true" />
        <span>보유자산 저장 중</span>
      </div>
    );
  }

  if (!result) return null;

  const imported = result.status === "imported";
  return (
    <div
      className={
        imported
          ? "rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-xs text-green-600 dark:text-green-400"
          : "rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-700 dark:text-yellow-300"
      }
      data-testid="upload-import-status"
    >
      <div className="flex items-center gap-2">
        {imported ? (
          <CheckCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        )}
        <span className="font-medium">
          {imported
            ? `${result.clientId} 보유자산 ${result.importedRows}건 저장`
            : "보유자산 매핑 확인 필요"}
        </span>
      </div>
      {!imported && result.warnings.length > 0 && (
        <p className="mt-1 pl-6 text-muted-foreground">{result.warnings[0]}</p>
      )}
      {imported && result.warnings.length > 0 && (
        <p className="mt-1 pl-6 text-muted-foreground">{result.warnings[0]}</p>
      )}
    </div>
  );
}

export default function UploadPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t } = useLocale();
  const clientsQuery = useQuery({
    queryKey: ["portfolio", "clients"],
    queryFn: getPortfolioClients,
    staleTime: 60_000,
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [config, setConfig] = useState<AnalyzerConfig>(DEFAULT_CONFIG);
  const [importing, setImporting] = useState(false);
  const [importedClient, setImportedClient] =
    useState<UploadedClientImportResult | null>(null);
  const [clientMode, setClientMode] = useState<UploadImportClientMode>("new");
  const [selectedExistingClientId, setSelectedExistingClientId] = useState("");

  const clients = clientsQuery.data?.clients ?? [];
  const existingClientIds = useMemo(
    () => clients.map((client) => client.client_id),
    [clients],
  );
  const generatedClientId = useMemo(
    () => getNextPortfolioClientId(existingClientIds),
    [existingClientIds],
  );
  const hasUploadResult = Boolean(validationResult) || Boolean(importedClient);
  const clientSelectionDisabled =
    uploading || validationLoading || importing || hasUploadResult;
  const displayedGeneratedClientId =
    clientMode === "new" && importedClient?.clientId
      ? importedClient.clientId
      : generatedClientId;

  useEffect(() => {
    if (selectedExistingClientId || clients.length === 0) return;
    setSelectedExistingClientId(clients[0]!.client_id);
  }, [clients, selectedExistingClientId]);

  const refreshPortfolioCaches = useCallback(
    async (clientId: string) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["portfolio", "clients"] }),
        queryClient.invalidateQueries({ queryKey: ["portfolio", "summary", clientId] }),
        queryClient.invalidateQueries({ queryKey: ["portfolio"] }),
      ]);
    },
    [queryClient],
  );

  const buildClientSelection = useCallback((): UploadImportClientSelection | null => {
    if (clientMode === "existing") {
      if (!selectedExistingClientId) return null;
      return {
        mode: "existing",
        clientId: selectedExistingClientId,
        existingClientIds,
      };
    }

    return clientsQuery.data
      ? {
          mode: "new",
          clientId: generatedClientId,
          existingClientIds,
        }
      : { mode: "new" };
  }, [
    clientMode,
    clientsQuery.data,
    existingClientIds,
    generatedClientId,
    selectedExistingClientId,
  ]);

  const handleFileAccepted = useCallback(async (file: File) => {
    const clientSelection = buildClientSelection();
    if (!clientSelection) {
      setValidationError("기존 고객을 선택해 주세요.");
      return;
    }

    setSelectedFile(file);
    setValidationResult(null);
    setValidationError(null);
    setImportedClient(null);
    setImporting(false);
    setUploading(true);
    setUploadProgress(0);

    // 진행률 시뮬레이션
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return prev;
        }
        return prev + 15;
      });
    }, 120);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/upload/csv`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!res.ok) {
        throw new Error(`업로드 실패 (${res.status})`);
      }

      const result = (await res.json()) as ValidationResult;
      setValidationLoading(true);
      // 짧은 딜레이로 로딩 UX 표시
      setTimeout(() => {
        setValidationResult(result);
        setValidationLoading(false);

        if (result.error_rows > 0 || result.valid_rows === 0) {
          setUploading(false);
          return;
        }

        setImporting(true);
        void importPortfolioCsvAsClient(result.upload_id, clientSelection)
          .then(async (importResult) => {
            setImportedClient(importResult);
            if (importResult.status === "imported") {
              await refreshPortfolioCaches(importResult.clientId);
            }
          })
          .catch((e) => {
            setValidationError(
              e instanceof Error ? `보유자산 저장 실패: ${e.message}` : "보유자산 저장 실패",
            );
          })
          .finally(() => {
            setImporting(false);
            setUploading(false);
          });
      }, 300);
    } catch (e) {
      clearInterval(progressInterval);
      setValidationError(e instanceof Error ? e.message : "업로드 중 오류 발생");
      setUploading(false);
      setUploadProgress(0);
    }
  }, [buildClientSelection, refreshPortfolioCaches]);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setValidationResult(null);
    setValidationError(null);
    setUploadProgress(0);
    setUploading(false);
    setImporting(false);
    setImportedClient(null);
  }, []);

  const handleAnalyzeComplete = useCallback(() => {
    if (importedClient?.status === "imported" && importedClient.clientId) {
      router.push(`/clients/${encodeURIComponent(importedClient.clientId)}`);
      return;
    }
    router.push("/");
  }, [importedClient?.clientId, importedClient?.status, router]);

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("upload.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("upload.subtitle")}</p>
      </div>

      {/* 메인 그리드 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ClientTargetPanel
          mode={clientMode}
          clients={clients}
          selectedExistingClientId={selectedExistingClientId}
          generatedClientId={displayedGeneratedClientId}
          loading={clientsQuery.isLoading}
          disabled={clientSelectionDisabled}
          onModeChange={setClientMode}
          onExistingClientChange={setSelectedExistingClientId}
        />

        {/* 1. 파일 업로드 */}
        <DropzoneCard
          onFileAccepted={handleFileAccepted}
          uploading={uploading}
          uploadProgress={uploadProgress}
          uploadedFile={selectedFile}
          onClear={handleClear}
        />

        {/* 2. 데이터 검증 상태 */}
        <div className="space-y-3">
          <ValidationCard
            result={validationResult}
            loading={validationLoading}
            error={validationError}
          />
          <ImportStatusPanel result={importedClient} importing={importing} />
        </div>

        {/* 3. 데이터 미리보기 */}
        <PreviewTable
          columns={getPreviewColumns(validationResult)}
          rows={getPreviewRows(validationResult)}
          loading={validationLoading}
        />

        {/* 4. 분석 설정 */}
        <AnalyzerConfigCard
          config={config}
          onChange={setConfig}
          disabled={uploading || validationLoading}
        />

        {/* 5. 분석 진행 상태 (전체 너비) */}
        <div className="md:col-span-2">
          <AnalyzeProgressCard
            uploadId={validationResult?.upload_id ?? null}
            config={config}
            disabled={
              !validationResult ||
              uploading ||
              validationLoading ||
              importedClient?.status !== "imported"
            }
            onComplete={handleAnalyzeComplete}
          />
        </div>
      </div>

      {/* 하단 — 템플릿 + FAQ */}
      <CsvTemplateCard />
    </div>
  );
}
