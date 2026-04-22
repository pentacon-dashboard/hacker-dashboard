"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface DegradedCardProps {
  reason: string;
  stepId?: string;
}

/**
 * DegradedCard — 게이트 실패 시 표시되는 경고 카드.
 *
 * shadcn Alert (variant="destructive") 기반.
 * reason 텍스트를 `aria-live="polite"` 로 읽힘.
 */
export function DegradedCard({ reason, stepId }: DegradedCardProps) {
  return (
    <div aria-live="polite" data-testid="copilot-degraded-card">
      <Alert variant="destructive" className="border-2">
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
          aria-hidden="true"
          className="h-4 w-4"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" x2="12" y1="8" y2="12" />
          <line x1="12" x2="12.01" y1="16" y2="16" />
        </svg>
        <AlertTitle>
          분석 품질 저하{stepId ? ` (${stepId})` : ""}
        </AlertTitle>
        <AlertDescription>{reason}</AlertDescription>
      </Alert>
    </div>
  );
}
