"use client";

import { useState } from "react";

export interface MonthlyReturnCell {
  date: string; // "YYYY-MM-DD"
  return_pct: string;
  cell_level: number; // 0~4
}

interface MonthlyReturnCalendarProps {
  cells: MonthlyReturnCell[];
  year?: number;
}

const MONTH_LABELS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const WEEK_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** cell_level 0~4 + 부호 → GitHub 스타일 색상 */
function levelToColor(level: number, returnPct: number): string {
  if (level === 0) return "bg-muted/50 dark:bg-muted/20";
  const positive = returnPct >= 0;
  if (positive) {
    switch (level) {
      case 1: return "bg-emerald-200 dark:bg-emerald-900/60";
      case 2: return "bg-emerald-400 dark:bg-emerald-700";
      case 3: return "bg-emerald-600 dark:bg-emerald-500";
      case 4: return "bg-emerald-800 dark:bg-emerald-400";
      default: return "bg-muted";
    }
  } else {
    switch (level) {
      case 1: return "bg-red-200 dark:bg-red-900/60";
      case 2: return "bg-red-400 dark:bg-red-700";
      case 3: return "bg-red-600 dark:bg-red-500";
      case 4: return "bg-red-800 dark:bg-red-400";
      default: return "bg-muted";
    }
  }
}

interface CellMap {
  [dateKey: string]: MonthlyReturnCell;
}

export function MonthlyReturnCalendar({ cells, year }: MonthlyReturnCalendarProps) {
  const [hovered, setHovered] = useState<MonthlyReturnCell | null>(null);

  if (cells.length === 0) {
    return (
      <div
        className="flex h-32 items-center justify-center text-sm text-muted-foreground"
        data-testid="monthly-return-calendar-empty"
      >
        수익률 데이터 없음
      </div>
    );
  }

  const displayYear = year ?? new Date().getFullYear();

  // 날짜 맵 구성
  const cellMap: CellMap = {};
  for (const c of cells) {
    cellMap[c.date] = c;
  }

  // 연도의 첫날
  const firstDay = new Date(displayYear, 0, 1);
  // 첫 번째 일요일 시작 기준으로 열(week) 계산
  const startOffset = firstDay.getDay(); // 0=Sun
  const totalWeeks = Math.ceil((365 + startOffset) / 7) + 1; // 53 or 54

  // 전체 격자 구성: [weekIndex][dayIndex]
  const grid: Array<Array<MonthlyReturnCell | null>> = [];
  for (let w = 0; w < totalWeeks; w++) {
    const week: Array<MonthlyReturnCell | null> = [];
    for (let d = 0; d < 7; d++) {
      const dayOffset = w * 7 + d - startOffset;
      if (dayOffset < 0 || dayOffset >= 365 + (isLeapYear(displayYear) ? 1 : 0)) {
        week.push(null);
      } else {
        const date = new Date(displayYear, 0, 1 + dayOffset);
        const iso = date.toISOString().slice(0, 10);
        week.push(cellMap[iso] ?? null);
      }
    }
    grid.push(week);
  }

  // 월 라벨 위치 계산 (각 월 첫 날이 속한 week 인덱스)
  const monthPositions: Array<{ label: string; weekIdx: number }> = [];
  for (let m = 0; m < 12; m++) {
    const firstOfMonth = new Date(displayYear, m, 1);
    const dayOfYear = Math.floor(
      (firstOfMonth.getTime() - firstDay.getTime()) / 86400000,
    );
    const weekIdx = Math.floor((dayOfYear + startOffset) / 7);
    monthPositions.push({ label: MONTH_LABELS[m] ?? "", weekIdx });
  }

  return (
    <div className="w-full overflow-x-auto" data-testid="monthly-return-calendar">
      <div className="relative min-w-[600px]">
        {/* 월 라벨 */}
        <div className="relative mb-1 flex h-4">
          {monthPositions.map(({ label, weekIdx }) => (
            <span
              key={label}
              className="absolute text-[10px] text-muted-foreground"
              style={{ left: `${(weekIdx / totalWeeks) * 100}%` }}
            >
              {label}
            </span>
          ))}
        </div>

        <div className="flex gap-[3px]">
          {/* 요일 라벨 */}
          <div className="flex flex-col gap-[3px] pr-1">
            {WEEK_LABELS.map((d, i) => (
              <span
                key={d}
                className="h-[11px] text-[9px] leading-[11px] text-muted-foreground"
              >
                {i % 2 === 1 ? d.slice(0, 1) : ""}
              </span>
            ))}
          </div>

          {/* 격자 */}
          {grid.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-[3px]">
              {week.map((cell, di) => {
                if (!cell) {
                  return <div key={di} className="h-[11px] w-[11px] rounded-[2px]" />;
                }
                const retNum = Number(cell.return_pct);
                const colorCls = levelToColor(cell.cell_level, retNum);
                return (
                  <div
                    key={di}
                    className={`h-[11px] w-[11px] rounded-[2px] ${colorCls} cursor-pointer transition-opacity hover:opacity-80`}
                    data-testid="calendar-cell"
                    title={`${cell.date}: ${retNum > 0 ? "+" : ""}${retNum.toFixed(2)}%`}
                    onMouseEnter={() => setHovered(cell)}
                    onMouseLeave={() => setHovered(null)}
                    role="img"
                    aria-label={`${cell.date} 수익률 ${retNum.toFixed(2)}%`}
                  />
                );
              })}
            </div>
          ))}
        </div>

        {/* 범례 */}
        <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
          <span>낮음</span>
          {[1, 2, 3, 4].map((lvl) => (
            <div
              key={lvl}
              className={`h-[10px] w-[10px] rounded-[2px] ${levelToColor(lvl, 1)}`}
            />
          ))}
          <span>높음</span>
        </div>
      </div>

      {/* 호버 툴팁 */}
      {hovered && (
        <div
          className="mt-1 rounded border bg-popover px-2 py-1 text-xs shadow"
          role="status"
        >
          {hovered.date}: {Number(hovered.return_pct) > 0 ? "+" : ""}
          {Number(hovered.return_pct).toFixed(2)}%
        </div>
      )}
    </div>
  );
}

function isLeapYear(y: number): boolean {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}
