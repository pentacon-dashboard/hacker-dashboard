"use client";

import { cn } from "@/lib/utils";

interface SectionCardProps {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  testId?: string;
}

export function SectionCard({
  title,
  action,
  children,
  className,
  testId,
}: SectionCardProps) {
  return (
    <section
      className={cn(
        "rounded-xl border bg-card p-4 shadow-sm",
        "flex min-w-0 flex-col",
        className,
      )}
      data-testid={testId}
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
