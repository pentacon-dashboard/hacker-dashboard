"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { searchNews, type Citation } from "@/lib/api/news";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocale } from "@/lib/i18n/locale-provider";

interface NewsPanelProps {
  symbols: string[];
  query?: string;
  limit?: number;
}

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function NewsPanel({ symbols, query, limit = 5 }: NewsPanelProps) {
  const { t, locale } = useLocale();
  const [items, setItems] = useState<Citation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [brokenIds, setBrokenIds] = useState<Set<string>>(new Set());

  function formatPublished(iso: string | null | undefined): string {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleDateString(locale === "en" ? "en-US" : "ko-KR", { month: "short", day: "numeric" });
    } catch {
      return "";
    }
  }

  useEffect(() => {
    let cancelled = false;
    const effectiveQuery =
      query ?? (symbols.length > 0 ? `${symbols[0]} 관련 최신 뉴스` : "시장 동향");
    setItems(null);
    setError(null);

    searchNews({
      query: effectiveQuery,
      symbols: symbols.length > 0 ? symbols : undefined,
      k: limit,
    })
      .then((res) => {
        if (!cancelled) setItems(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("news.loadFail"));
          setItems([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [symbols.join(","), query, limit]);

  if (items === null) {
    return (
      <div className="space-y-3" data-testid="news-panel-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-12 w-12 shrink-0 rounded" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3 w-11/12" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div
        className="flex h-48 items-center justify-center text-sm text-muted-foreground"
        data-testid="news-panel-empty"
      >
        {error ?? t("news.noRelated")}
      </div>
    );
  }

  return (
    <ul className="space-y-3" data-testid="news-panel">
      {items.map((c) => (
        <li key={`${c.doc_id}-${c.chunk_id}`}>
          <a
            href={c.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex gap-3 rounded-md p-1.5 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {c.thumbnail_url && !brokenIds.has(`${c.doc_id}-${c.chunk_id}`) ? (
              <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded bg-muted">
                <Image
                  src={c.thumbnail_url}
                  alt=""
                  fill
                  sizes="48px"
                  className="object-cover"
                  unoptimized
                  onError={() =>
                    setBrokenIds((prev) => new Set(prev).add(`${c.doc_id}-${c.chunk_id}`))
                  }
                />
              </div>
            ) : (
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-muted text-[10px] font-semibold uppercase text-muted-foreground">
                {hostname(c.source_url).slice(0, 4)}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{c.title}</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {hostname(c.source_url)}
                {c.published_at ? ` · ${formatPublished(c.published_at)}` : ""}
              </p>
            </div>
          </a>
        </li>
      ))}
    </ul>
  );
}
