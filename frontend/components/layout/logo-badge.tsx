"use client";

import { cn } from "@/lib/utils";

interface LogoBadgeProps {
  collapsed?: boolean;
  className?: string;
}

/**
 * 사이드바 최상단 로고 배지.
 * - 펼침: "HACKER" + "DASHBOARD" 두 줄, 보라색 배지 박스
 * - 접힘: "HD" 약식 배지
 */
export function LogoBadge({ collapsed = false, className }: LogoBadgeProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center",
        collapsed ? "px-1" : "px-3",
        className,
      )}
      aria-label="Hacker Dashboard 로고"
    >
      {collapsed ? (
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shadow-sm">
          <span className="text-xs font-black tracking-wider text-primary-foreground">
            HD
          </span>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl bg-primary px-3 py-1.5 shadow-sm">
          <span className="text-[10px] font-black tracking-[0.2em] text-primary-foreground/90 leading-none">
            HACKER
          </span>
          <span className="text-[8px] font-semibold tracking-[0.25em] text-primary-foreground/70 leading-none mt-0.5">
            DASHBOARD
          </span>
        </div>
      )}
    </div>
  );
}
