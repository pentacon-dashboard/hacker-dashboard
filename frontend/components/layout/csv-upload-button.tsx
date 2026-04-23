"use client";

import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * CsvUploadButton — 헤더 우측 CSV 업로드 버튼.
 * - outline variant, Upload 아이콘 + "CSV 업로드" 라벨
 * - 클릭 시 /upload 라우트로 이동
 */
export function CsvUploadButton() {
  const router = useRouter();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => router.push("/upload")}
      className="h-8 gap-1.5 text-xs px-2.5"
      aria-label="CSV 파일 업로드"
      data-testid="csv-upload-button"
    >
      <Upload className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="hidden sm:inline">CSV 업로드</span>
    </Button>
  );
}
