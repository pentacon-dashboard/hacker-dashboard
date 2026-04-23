"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { DayPicker } from "react-day-picker";
import { ko } from "react-day-picker/locale";
import type { DateRange } from "react-day-picker";
import { CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

function formatKoDate(date: Date): string {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function getDefaultRange(): DateRange {
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - 30);
  return { from, to };
}

/**
 * DateRangePicker — 헤더 우측 날짜 범위 선택기.
 * - react-day-picker v9 + shadcn Popover 스타일 직접 구현
 * - 기본값: 최근 30일
 * - URL query string (?from=YYYY-MM-DD&to=YYYY-MM-DD) 동기화
 */
export function DateRangePicker() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);

  // URL에서 초기값 파싱
  const initialRange = useCallback((): DateRange => {
    const fromParam = searchParams.get("from");
    const toParam = searchParams.get("to");
    if (fromParam && toParam) {
      const from = new Date(fromParam);
      const to = new Date(toParam);
      if (!isNaN(from.getTime()) && !isNaN(to.getTime())) {
        return { from, to };
      }
    }
    return getDefaultRange();
  }, [searchParams]);

  const [range, setRange] = useState<DateRange>(initialRange);

  // URL query string 동기화
  const syncToUrl = useCallback(
    (r: DateRange) => {
      if (!r.from || !r.to) return;
      const params = new URLSearchParams(searchParams.toString());
      params.set("from", r.from.toISOString().split("T")[0]!);
      params.set("to", r.to.toISOString().split("T")[0]!);
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const handleSelect = useCallback(
    (selected: DateRange | undefined) => {
      if (!selected) return;
      setRange(selected);
      if (selected.from && selected.to) {
        syncToUrl(selected);
        setOpen(false);
      }
    },
    [syncToUrl],
  );

  // 바깥 클릭으로 팝오버 닫기
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        open &&
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        !triggerRef.current?.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const label =
    range.from && range.to
      ? `${formatKoDate(range.from)} – ${formatKoDate(range.to)}`
      : "날짜 선택";

  return (
    <div className="relative" data-testid="date-range-picker">
      <Button
        ref={triggerRef}
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`날짜 범위: ${label}`}
        className="h-8 gap-1.5 text-xs px-2.5"
      >
        <CalendarIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="hidden sm:inline">{label}</span>
      </Button>

      {open && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-label="날짜 범위 선택"
          className={cn(
            "absolute right-0 top-full z-50 mt-1.5 rounded-2xl border border-border bg-popover shadow-lg",
            "animate-in fade-in duration-200",
          )}
        >
          <DayPicker
            mode="range"
            locale={ko}
            selected={range}
            onSelect={handleSelect}
            numberOfMonths={2}
            className="p-3"
            classNames={{
              root: "rdp",
              months: "flex gap-4",
              month: "flex flex-col gap-1",
              caption: "flex items-center justify-between py-1 mb-1",
              caption_label: "text-sm font-semibold text-foreground",
              nav: "flex items-center gap-1",
              button_previous: "h-6 w-6 rounded-lg hover:bg-muted flex items-center justify-center text-muted-foreground",
              button_next: "h-6 w-6 rounded-lg hover:bg-muted flex items-center justify-center text-muted-foreground",
              table: "w-full border-collapse",
              head_row: "flex",
              head_cell: "w-8 text-center text-[10px] text-muted-foreground font-normal py-1",
              row: "flex mt-0.5",
              cell: "w-8 text-center text-sm p-0",
              day: "h-7 w-7 rounded-lg text-xs font-medium hover:bg-muted flex items-center justify-center mx-auto transition-colors",
              day_selected: "bg-violet-600 text-white hover:bg-violet-700",
              day_range_middle: "rounded-none bg-violet-600/20 text-violet-400",
              day_today: "font-bold text-violet-400",
              day_outside: "text-muted-foreground/40",
              day_disabled: "text-muted-foreground/30 cursor-not-allowed",
            }}
          />
        </div>
      )}
    </div>
  );
}
