"use client";

import type { CopilotCard } from "@/hooks/use-copilot-stream";

interface TextCardProps {
  card: CopilotCard & { type: "text"; body?: string; content?: string };
}

export function TextCard({ card }: TextCardProps) {
  const text = card.content ?? card.body ?? "";
  return (
    <div className="rounded-md border bg-card p-4 text-sm text-card-foreground">
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  );
}
