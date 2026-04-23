"use client";

import { Download, HelpCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";

const FAQ_ITEMS = [
  {
    q: "어떤 CSV 형식을 지원하나요?",
    a: "date, symbol, quantity, price, currency 컬럼을 포함한 CSV 파일을 지원합니다. 컬럼 순서는 무관하며, 헤더 행이 반드시 포함되어야 합니다.",
  },
  {
    q: "분석에 얼마나 걸리나요?",
    a: "보통 5초 이내에 분석이 완료됩니다. Router → 스키마 → 도메인 → AI self-critique 4단계 게이트를 거쳐 대시보드가 자동 생성됩니다.",
  },
  {
    q: "지원하는 자산 유형은?",
    a: "주식(국내·미국), 암호화폐(업비트·바이낸스), ETF, 환율 포지션을 지원합니다. AI가 CSV를 분석하여 적절한 Analyzer를 자동 선택합니다.",
  },
  {
    q: "오류/경고 행이 있으면 분석이 가능한가요?",
    a: "오류 행은 분석에서 제외되고, 경고 행은 포함됩니다. 오류율이 50% 초과 시 분석이 차단됩니다.",
  },
  {
    q: "데이터는 안전하게 처리되나요?",
    a: "업로드된 파일은 분석 완료 후 24시간 내 자동 삭제됩니다. 실거래 API 키나 개인 식별 정보를 포함하지 마세요.",
  },
];

export function CsvTemplateCard() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  function handleDownload() {
    window.open(`${API_BASE}/upload/template`, "_blank");
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {/* 템플릿 다운로드 */}
      <Card data-testid="csv-template-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Download className="h-4 w-4 text-primary" aria-hidden="true" />
            CSV 템플릿 다운로드
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            올바른 CSV 형식의 샘플 파일을 다운로드하세요. 실제 데이터로 교체 후 업로드하시면 됩니다.
          </p>
          <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground">
            <p>date,symbol,quantity,price,currency</p>
            <p>2024-01-15,AAPL,12,182.5,USD</p>
            <p>2024-01-15,005930.KS,40,71000,KRW</p>
            <p className="text-muted-foreground/50">...</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={handleDownload}
            data-testid="template-download-btn"
          >
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            portfolio_template.csv 다운로드
          </Button>
        </CardContent>
      </Card>

      {/* FAQ */}
      <Card data-testid="faq-panel">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <HelpCircle className="h-4 w-4 text-primary" aria-hidden="true" />
            자주 묻는 질문
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {FAQ_ITEMS.map((item, i) => (
            <div key={i} className="border-b border-border last:border-0">
              <button
                className="flex w-full items-center justify-between py-2 text-left text-xs font-medium hover:text-primary transition-colors"
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                aria-expanded={openIdx === i}
              >
                <span>{item.q}</span>
                {openIdx === i ? (
                  <ChevronUp className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
                ) : (
                  <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
                )}
              </button>
              {openIdx === i && (
                <p className="pb-2 text-xs text-muted-foreground">{item.a}</p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
