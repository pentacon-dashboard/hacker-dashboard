"use client";

import { useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { analyzeCsv, type AnalyzeResponse } from "@/lib/api/analyze";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface CsvDropzoneProps {
  onResult: (data: { response: AnalyzeResponse; cacheHeader: string | null }) => void;
  onError: (message: string) => void;
  className?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CsvDropzone({ onResult, onError, className }: CsvDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileSizeError, setFileSizeError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const validateAndSetFile = useCallback((file: File) => {
    if (!file.name.endsWith(".csv")) {
      setFileSizeError("CSV 파일만 업로드할 수 있습니다.");
      setSelectedFile(null);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setFileSizeError(`파일 크기가 10MB를 초과합니다. (현재: ${formatBytes(file.size)})`);
      setSelectedFile(null);
      return;
    }
    setFileSizeError(null);
    setSelectedFile(file);
  }, []);

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetFile(file);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) validateAndSetFile(file);
  }

  function handleClick() {
    inputRef.current?.click();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  }

  async function handleSubmit() {
    if (!selectedFile) return;
    setIsLoading(true);
    try {
      const result = await analyzeCsv(selectedFile);
      onResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.";
      onError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className={cn("space-y-4", className)} data-testid="csv-dropzone">
      <div
        role="button"
        tabIndex={0}
        aria-label="CSV 파일을 드래그하거나 클릭하여 업로드"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 text-center transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/60 hover:bg-muted/40",
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground"
          aria-hidden="true"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" x2="12" y1="3" y2="15" />
        </svg>
        <div className="space-y-1">
          <p className="text-sm font-medium">CSV 파일을 여기에 끌어다 놓거나 클릭하여 선택</p>
          <p className="text-xs text-muted-foreground">최대 10MB, .csv 형식만 지원</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="sr-only"
          onChange={handleInputChange}
          aria-hidden="true"
          tabIndex={-1}
        />
      </div>

      {fileSizeError && (
        <p className="text-sm font-medium text-destructive" role="alert" data-testid="csv-file-error">
          {fileSizeError}
        </p>
      )}

      {selectedFile && !fileSizeError && (
        <div
          className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2 text-sm"
          data-testid="csv-file-label"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="shrink-0 text-muted-foreground"
            aria-hidden="true"
          >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className="min-w-0 flex-1 truncate font-medium">{selectedFile.name}</span>
          <span className="shrink-0 text-muted-foreground">{formatBytes(selectedFile.size)}</span>
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!selectedFile || !!fileSizeError || isLoading}
        aria-label="CSV 파일 분석 시작"
        data-testid="csv-submit"
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "bg-primary text-primary-foreground hover:bg-primary/90",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        {isLoading ? (
          <>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animate-spin"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            분석 중...
          </>
        ) : (
          "분석 시작"
        )}
      </button>
    </div>
  );
}
