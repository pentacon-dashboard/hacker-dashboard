"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, File, X, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface DropzoneCardProps {
  onFileAccepted: (file: File) => void;
  uploading?: boolean;
  uploadProgress?: number;
  uploadedFile?: File | null;
  onClear?: () => void;
}

export function DropzoneCard({
  onFileAccepted,
  uploading = false,
  uploadProgress = 0,
  uploadedFile,
  onClear,
}: DropzoneCardProps) {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (file) onFileAccepted(file);
    },
    [onFileAccepted],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.ms-excel": [".csv"] },
    maxFiles: 1,
    disabled: uploading,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
  });

  return (
    <Card data-testid="dropzone-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">1. 파일 업로드</CardTitle>
        <p className="text-xs text-muted-foreground">
          CSV 파일을 드래그하거나 클릭하여 업로드하세요. 업로드된 파일을 분석하여 대시보드를 자동 생성합니다.
        </p>
      </CardHeader>
      <CardContent>
        {uploadedFile && !uploading ? (
          <div className="flex items-center gap-3 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3">
            <CheckCircle className="h-5 w-5 shrink-0 text-green-500" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{uploadedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {(uploadedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
            {onClear && (
              <button
                onClick={onClear}
                aria-label="파일 제거"
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        ) : uploading ? (
          <div className="space-y-2 rounded-lg border border-border bg-muted/30 px-4 py-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <File className="h-4 w-4" />
              <span className="truncate">{uploadedFile?.name ?? "업로드 중..."}</span>
              <span className="ml-auto text-xs">{uploadProgress}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
                role="progressbar"
                aria-valuenow={uploadProgress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        ) : (
          <div
            {...getRootProps()}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 transition-colors",
              isDragActive || dragActive
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 hover:bg-muted/30",
            )}
            aria-label="CSV 파일 업로드 영역"
          >
            <input {...getInputProps()} data-testid="file-input" />
            <Upload
              className={cn(
                "h-10 w-10 transition-colors",
                isDragActive ? "text-primary" : "text-muted-foreground",
              )}
              aria-hidden="true"
            />
            <div className="text-center">
              <p className="text-sm font-medium">
                {isDragActive ? "파일을 놓으세요" : "CSV 파일을 드래그하거나 클릭"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                .csv 형식 지원 · 최대 10MB
              </p>
            </div>
            <Button variant="outline" size="sm" tabIndex={-1} aria-hidden="true">
              파일 선택
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
