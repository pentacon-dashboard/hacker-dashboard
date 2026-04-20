"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { searchSymbols, type SymbolInfo } from "@/lib/api/symbols";
import { AssetBadge } from "@/components/common/asset-badge";

interface SymbolSearchProps {
  onSelect: (symbol: SymbolInfo) => void;
}

export function SymbolSearch({ onSelect }: SymbolSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.trim().length === 0) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const data = await searchSymbols(q);
      setResults(data);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void search(query);
    }, 300);
    return () => {
      if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    };
  }, [query, search]);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(symbol: SymbolInfo) {
    onSelect(symbol);
    setQuery("");
    setResults([]);
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-sm">
      <input
        type="search"
        data-testid="symbol-search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="종목 검색 (예: BTC, AAPL)"
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label="종목 검색"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls="symbol-search-listbox"
        autoComplete="off"
      />
      {loading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <span
            className="h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-foreground block"
            aria-hidden="true"
          />
        </div>
      )}
      {open && results.length > 0 && (
        <ul
          id="symbol-search-listbox"
          role="listbox"
          aria-label="검색 결과"
          className="absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-popover shadow-md"
        >
          {results.map((item) => (
            <li
              key={`${item.market}:${item.symbol}`}
              role="option"
              aria-selected={false}
              className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-accent focus:bg-accent outline-none"
              onClick={() => handleSelect(item)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") handleSelect(item);
              }}
              tabIndex={0}
            >
              <span className="font-medium">{item.symbol}</span>
              <span className="mx-2 flex-1 truncate text-muted-foreground">
                {item.name}
              </span>
              <AssetBadge assetClass={item.asset_class} />
            </li>
          ))}
        </ul>
      )}
      {open && !loading && results.length === 0 && query.trim().length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover px-3 py-4 text-center text-sm text-muted-foreground shadow-md">
          결과 없음
        </div>
      )}
    </div>
  );
}
