"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { DayPicker } from "react-day-picker";
import { ko, enUS } from "react-day-picker/locale";
import type { DateRange } from "react-day-picker";
import { CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-provider";

function formatDate(date: Date, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, {
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
  const { locale, t } = useLocale();
  const dpLocale = locale === "en" ? enUS : ko;
  const localeTag = locale === "en" ? "en-US" : "ko-KR";

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
      ? `${formatDate(range.from, localeTag)} – ${formatDate(range.to, localeTag)}`
      : t("header.dateRangeSelect");

  return (
    <div className="relative" data-testid="date-range-picker">
      <Button
        ref={triggerRef}
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={t("header.dateRangeAria", { label })}
        className="h-8 gap-1.5 text-xs px-2.5"
      >
        <CalendarIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="hidden sm:inline">{label}</span>
      </Button>

      {open && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-label={t("header.dateRangePicker")}
          className={cn(
            "absolute right-0 top-full z-50 mt-1.5 rounded-2xl border border-border bg-popover shadow-lg",
            "w-[min(32rem,calc(100vw-2rem))] overflow-x-auto animate-in fade-in duration-200 sm:w-auto",
          )}
        >
          <DayPicker
            mode="range"
            locale={dpLocale}
            selected={range}
            onSelect={handleSelect}
            numberOfMonths={2}
            fixedWeeks
            className="p-3"
            classNames={{
              root: "rdp",
              months: "flex flex-col gap-4 sm:flex-row",
              month: "w-56 space-y-2",
              month_caption: "relative flex h-8 items-center justify-center",
              caption_label: "text-sm font-semibold text-foreground",
              nav: "absolute inset-x-3 top-3 flex items-center justify-between",
              button_previous: "h-7 w-7 rounded-lg hover:bg-muted flex items-center justify-center text-muted-foreground",
              button_next: "h-7 w-7 rounded-lg hover:bg-muted flex items-center justify-center text-muted-foreground",
              month_grid: "w-56 table-fixed border-collapse",
              weekdays: "",
              weekday: "h-7 w-8 text-center text-[10px] font-medium leading-7 text-muted-foreground",
              week: "",
              day: "h-8 w-8 p-0 text-center text-sm",
              day_button: "mx-auto flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors hover:bg-muted",
              selected: "bg-primary text-primary-foreground hover:bg-primary/90",
              range_start: "rounded-l-lg bg-primary text-primary-foreground",
              range_middle: "rounded-none bg-primary/20 text-primary",
              range_end: "rounded-r-lg bg-primary text-primary-foreground",
              today: "font-bold text-primary",
              outside: "text-muted-foreground/40",
              disabled: "cursor-not-allowed text-muted-foreground/30",
            }}
          />
        </div>
      )}
    </div>
  );
}
