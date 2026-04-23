"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import { apiFetch } from "@/lib/api/client";
import type { components } from "@shared/types/api";
import { ExternalLink } from "lucide-react";

type Citation = components["schemas"]["Citation"];

interface SymbolNewsPanelProps {
  symbol?: string;
  limit?: number;
}

async function fetchNews(symbol?: string, limit = 5): Promise<Citation[]> {
  const params = new URLSearchParams({ k: String(limit) });
  if (symbol) params.set("symbols", symbol);
  return apiFetch<Citation[]>(`/search/news?${params.toString()}`);
}

function NewsItem({ item }: { item: Citation }) {
  const dateStr = item.published_at
    ? new Date(item.published_at).toLocaleDateString("ko-KR", {
        month: "short",
        day: "numeric",
      })
    : "";

  return (
    <li className="flex gap-3 rounded-lg p-2 hover:bg-muted/50 transition-colors">
      {item.thumbnail_url ? (
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md">
          <Image
            src={item.thumbnail_url}
            alt=""
            fill
            sizes="48px"
            className="object-cover"
            aria-hidden="true"
          />
        </div>
      ) : (
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-muted text-[10px] font-bold text-muted-foreground"
          aria-hidden="true"
        >
          {item.title.slice(0, 2)}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="line-clamp-2 text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {item.title}
          <ExternalLink className="ml-1 inline h-3 w-3" aria-hidden="true" />
        </a>
        <p className="mt-1 line-clamp-1 text-[10px] text-muted-foreground">
          {item.excerpt}
        </p>
        {dateStr && (
          <p className="mt-0.5 text-[10px] text-muted-foreground">{dateStr}</p>
        )}
      </div>
    </li>
  );
}

export function SymbolNewsPanel({ symbol, limit = 5 }: SymbolNewsPanelProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["news", symbol, limit],
    queryFn: () => fetchNews(symbol, limit),
    staleTime: 120_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="symbol-news-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-12 w-12 shrink-0 animate-pulse rounded-md bg-muted" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError || !data || data.length === 0) {
    return (
      <div
        className="flex h-24 items-center justify-center text-sm text-muted-foreground"
        data-testid="symbol-news-empty"
      >
        관련 뉴스 없음
      </div>
    );
  }

  return (
    <ul className="space-y-1" data-testid="symbol-news-panel">
      {data.map((item) => (
        <NewsItem key={item.chunk_id} item={item} />
      ))}
    </ul>
  );
}
