"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const { t } = useLocale();
  const resolvedTitle = title ?? t("common.emptyTitle");
  const resolvedDesc = description ?? t("common.emptyDesc");
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed p-8 text-center",
        className,
      )}
      role="status"
      aria-label={resolvedTitle}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground"
          aria-hidden="true"
        >
          <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" />
          <path d="M7 2v20" />
          <path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7" />
        </svg>
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-semibold">{resolvedTitle}</h3>
        <p className="text-sm text-muted-foreground">{resolvedDesc}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
