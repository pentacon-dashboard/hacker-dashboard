"use client";

import { useState } from "react";
import { Info, Trash2, CheckCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface SystemInfoProps {
  version?: string;
  apiStatus?: "healthy" | "degraded" | "error";
  buildTime?: string;
  cacheSizeMb?: number;
}

export function SystemInfo({
  version = "0.3.1-sprint-08",
  apiStatus = "healthy",
  buildTime,
  cacheSizeMb = 42,
}: SystemInfoProps) {
  const [cacheCleared, setCacheCleared] = useState(false);

  const formattedBuild = buildTime
    ? new Date(buildTime).toLocaleString("ko-KR")
    : new Date().toLocaleString("ko-KR");

  function handleClearCache() {
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 3000);
  }

  return (
    <Card data-testid="system-info">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Info className="h-4 w-4 text-primary" aria-hidden="true" />
          시스템 정보
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 정보 항목들 */}
        {[
          { label: "버전", value: version },
          { label: "빌드 시간", value: formattedBuild },
          { label: "캐시 크기", value: `${cacheSizeMb} MB` },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{item.label}</span>
            <span className="text-xs font-mono font-medium">{item.value}</span>
          </div>
        ))}

        {/* API 상태 */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">API 상태</span>
          <div className="flex items-center gap-1.5">
            {apiStatus === "healthy" ? (
              <>
                <CheckCircle className="h-3.5 w-3.5 text-green-500" aria-hidden="true" />
                <span className="text-xs font-medium text-green-500">정상</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
                <span className="text-xs font-medium text-destructive">
                  {apiStatus === "degraded" ? "성능 저하" : "오류"}
                </span>
              </>
            )}
          </div>
        </div>

        {/* 캐시 비우기 */}
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={handleClearCache}
          data-testid="clear-cache-btn"
        >
          {cacheCleared ? (
            <>
              <CheckCircle className="mr-2 h-3.5 w-3.5 text-green-500" aria-hidden="true" />
              캐시 삭제 완료
            </>
          ) : (
            <>
              <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
              캐시 비우기
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
