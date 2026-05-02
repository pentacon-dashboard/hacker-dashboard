"use client";

import { Download, HelpCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/locale-provider";

export function CsvTemplateCard() {
  const { t } = useLocale();
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const FAQ_ITEMS = [
    { q: t("upload.faq.q1"), a: t("upload.faq.a1") },
    { q: t("upload.faq.q2"), a: t("upload.faq.a2") },
    { q: t("upload.faq.q3"), a: t("upload.faq.a3") },
    { q: t("upload.faq.q4"), a: t("upload.faq.a4") },
    { q: t("upload.faq.q5"), a: t("upload.faq.a5") },
  ];

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
            {t("upload.templateDownload")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {t("upload.template.desc")}
          </p>
          <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground">
            <p>date,market,code,quantity,avg_cost,currency</p>
            <p>2024-01-15,yahoo,AAPL,12,182.5,USD</p>
            <p>2024-01-15,naver_kr,005930,40,71000,KRW</p>
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
            {t("upload.template.download")}
          </Button>
        </CardContent>
      </Card>

      {/* FAQ */}
      <Card data-testid="faq-panel">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <HelpCircle className="h-4 w-4 text-primary" aria-hidden="true" />
            {t("upload.faq")}
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
