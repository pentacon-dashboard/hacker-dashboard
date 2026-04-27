"use client";

import type { CopilotCard } from "@/hooks/use-copilot-stream";

interface TextCardProps {
  card: CopilotCard & { type: "text"; body?: string; content?: string };
}

function normalizeText(text: string): string {
  let cleaned = text.trim();
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim();

  try {
    const parsed = JSON.parse(cleaned) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      const data = parsed as Record<string, unknown>;
      for (const key of ["answer", "response", "content", "summary", "message", "analysis"]) {
        const value = data[key];
        if (typeof value === "string" && value.trim()) return value.trim();
      }
    }
  } catch {
    // Plain text is the normal path.
  }

  cleaned = cleaned.replace(/^\[[^\]]+\]\s*/gm, "");
  cleaned = cleaned.replace(/\s*\((?:sync fallback|degraded)\)\s*/gi, " ");
  cleaned = cleaned.replace(/(?:stock|crypto|fx|macro|portfolio|rebalance|포트폴리오)\s*분석\s*결과\s*:\s*/gi, "");
  cleaned = cleaned.replace(/sync fallback\s*:\s*/gi, "");
  return cleaned.trim();
}

export function TextCard({ card }: TextCardProps) {
  const text = normalizeText(card.content ?? card.body ?? "");
  return (
    <div className="rounded-md border bg-card p-4 text-sm text-card-foreground">
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  );
}
