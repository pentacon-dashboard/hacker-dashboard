"use client";

import { AlertCircle } from "lucide-react";

export interface KeyIssue {
  id: string;
  title: string;
  severity: "high" | "medium" | "low";
  date: string;
}

interface KeyIssueListProps {
  issues: KeyIssue[];
  isLoading?: boolean;
}

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  low: "bg-muted text-muted-foreground",
};

const SEVERITY_LABELS: Record<string, string> = {
  high: "고위험",
  medium: "중위험",
  low: "참고",
};

export function KeyIssueList({ issues, isLoading = false }: KeyIssueListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2" data-testid="key-issue-list-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div
        className="flex h-24 items-center justify-center text-sm text-muted-foreground"
        data-testid="key-issue-list-empty"
      >
        주요 이슈 없음
      </div>
    );
  }

  return (
    <ul className="space-y-2" data-testid="key-issue-list">
      {issues.map((issue) => {
        const style = SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES["low"]!;
        const label = SEVERITY_LABELS[issue.severity] ?? "참고";
        const dateStr = new Date(issue.date).toLocaleDateString("ko-KR", {
          month: "short",
          day: "numeric",
        });
        return (
          <li
            key={issue.id}
            className="flex items-start gap-2 rounded-lg border p-2"
            data-testid={`key-issue-${issue.id}`}
          >
            <AlertCircle
              className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium line-clamp-2">{issue.title}</p>
              <div className="mt-1 flex items-center gap-2">
                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${style}`}>
                  {label}
                </span>
                <span className="text-[10px] text-muted-foreground">{dateStr}</span>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
