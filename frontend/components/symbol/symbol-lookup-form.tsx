"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, Search } from "lucide-react";
import { AssetBadge } from "@/components/common/asset-badge";
import { searchSymbols, type SymbolInfo } from "@/lib/api/symbols";
import { getSymbolDisplayParts } from "@/lib/market/display";

const SEARCH_DEBOUNCE_MS = 250;

function symbolHref(market: string, code: string): string {
  return `/symbol/${encodeURIComponent(market)}/${encodeURIComponent(code)}`;
}

function fallbackSymbol(query: string): { market: string; code: string } | null {
  const raw = query.trim();
  const upper = raw.toUpperCase();

  if (!upper) return null;

  if (upper.startsWith("KRW-") || upper.startsWith("BTC-") || upper.startsWith("USDT-")) {
    return { market: "upbit", code: upper };
  }

  const domesticMatch = upper.match(/^(\d{6})(?:\.(KS|KQ))?$/u);
  if (domesticMatch) {
    return { market: "naver_kr", code: domesticMatch[1]! };
  }

  if (/^[A-Z][A-Z0-9.-]{0,15}$/u.test(upper)) {
    return { market: "yahoo", code: upper };
  }

  return null;
}

function routeToSymbol(router: ReturnType<typeof useRouter>, symbol: SymbolInfo) {
  router.push(symbolHref(symbol.market, symbol.symbol));
}

export function SymbolLookupForm() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    requestIdRef.current += 1;
    const requestId = requestIdRef.current;

    if (!trimmed) {
      setResults([]);
      setOpen(false);
      setLoading(false);
      setError(false);
      return;
    }

    const timer = setTimeout(() => {
      setLoading(true);
      setError(false);
      searchSymbols(trimmed)
        .then((items) => {
          if (requestIdRef.current !== requestId) return;
          setResults(items);
          setOpen(true);
        })
        .catch(() => {
          if (requestIdRef.current !== requestId) return;
          setResults([]);
          setOpen(true);
          setError(true);
        })
        .finally(() => {
          if (requestIdRef.current === requestId) setLoading(false);
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query]);

  const submitQuery = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    if (results.length > 0) {
      routeToSymbol(router, results[0]!);
      return;
    }

    setLoading(true);
    setError(false);
    try {
      const items = await searchSymbols(trimmed);
      if (items.length > 0) {
        routeToSymbol(router, items[0]!);
        return;
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }

    const fallback = fallbackSymbol(trimmed);
    if (fallback) {
      router.push(symbolHref(fallback.market, fallback.code));
    } else {
      setOpen(true);
      setResults([]);
    }
  }, [query, results, router]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void submitQuery();
  }

  return (
    <div className="relative">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-2 sm:flex-row"
        data-testid="symbol-lookup-form"
      >
        <label className="relative min-w-0 flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            role="searchbox"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => {
              if (query.trim()) setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void submitQuery();
              }
            }}
            placeholder="예: 삼성전자, NAVER, 카카오, NVDA, KRW-BTC"
            className="h-10 w-full rounded-md border border-border bg-background pl-9 pr-9 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="종목 검색"
            autoComplete="off"
          />
          {loading ? (
            <Loader2
              className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground"
              aria-hidden="true"
            />
          ) : null}
        </label>
        <button
          type="submit"
          onClick={(event) => {
            event.preventDefault();
            void submitQuery();
          }}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          분석
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>

      {open && query.trim().length > 0 ? (
        <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-md border bg-popover shadow-lg">
          {results.length > 0 ? (
            <ul className="max-h-72 overflow-auto p-1" role="listbox" aria-label="종목 검색 결과">
              {results.map((item) => {
                const displayParts = getSymbolDisplayParts(item.market, item.symbol, {
                  fallbackName: item.name,
                  includeMarket: true,
                });
                return (
                  <li key={`${item.market}:${item.symbol}`}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-3 rounded px-3 py-2 text-left text-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={() => routeToSymbol(router, item)}
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-foreground">
                          {displayParts.primary}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {displayParts.secondary ?? item.market}
                        </span>
                      </span>
                      <AssetBadge assetClass={item.asset_class} />
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="px-3 py-4 text-sm text-muted-foreground">
              {error
                ? "검색 결과를 불러오지 못했습니다. 직접 입력값으로 이동할 수 있으면 Enter를 눌러주세요."
                : "자동 매핑 결과가 없습니다. 6자리 코드, KRW-BTC, 영문 티커는 직접 이동합니다."}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
