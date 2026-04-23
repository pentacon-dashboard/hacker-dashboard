"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { DropzoneCard } from "@/components/upload/dropzone-card";
import { ValidationCard, type ValidationResult } from "@/components/upload/validation-card";
import { PreviewTable } from "@/components/upload/preview-table";
import { AnalyzerConfigCard, type AnalyzerConfig } from "@/components/upload/analyzer-config-card";
import { AnalyzeProgressCard } from "@/components/upload/analyze-progress-card";
import { CsvTemplateCard } from "@/components/upload/csv-template-card";
import { API_BASE } from "@/lib/api/client";

const DEFAULT_CONFIG: AnalyzerConfig = {
  analyzer: "portfolio",
  period_days: 90,
  currency: "KRW",
  include_fx: true,
};

export default function UploadPage() {
  const router = useRouter();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [config, setConfig] = useState<AnalyzerConfig>(DEFAULT_CONFIG);

  const handleFileAccepted = useCallback(async (file: File) => {
    setSelectedFile(file);
    setValidationResult(null);
    setValidationError(null);
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
        setUploading(false);
      }, 300);
    } catch (e) {
      clearInterval(progressInterval);
      setValidationError(e instanceof Error ? e.message : "업로드 중 오류 발생");
      setUploading(false);
      setUploadProgress(0);
    }
  }, []);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setValidationResult(null);
    setValidationError(null);
    setUploadProgress(0);
    setUploading(false);
  }, []);

  const handleAnalyzeComplete = useCallback(() => {
    router.push("/");
  }, [router]);

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">업로드 &amp; 분석</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          CSV 파일을 업로드하면 AI가 자동으로 분석 뷰를 생성합니다. 5초 내 대시보드 자동 진입.
        </p>
      </div>

      {/* 메인 그리드 — 2×3 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* 1. 파일 업로드 */}
        <DropzoneCard
          onFileAccepted={handleFileAccepted}
          uploading={uploading}
          uploadProgress={uploadProgress}
          uploadedFile={selectedFile}
          onClear={handleClear}
        />

        {/* 2. 데이터 검증 상태 */}
        <ValidationCard
          result={validationResult}
          loading={validationLoading}
          error={validationError}
        />

        {/* 3. 데이터 미리보기 */}
        <PreviewTable
          columns={validationResult?.columns_detected}
          rows={validationResult?.preview_rows}
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
            disabled={!validationResult || uploading || validationLoading}
            onComplete={handleAnalyzeComplete}
          />
        </div>
      </div>

      {/* 하단 — 템플릿 + FAQ */}
      <CsvTemplateCard />
    </div>
  );
}
