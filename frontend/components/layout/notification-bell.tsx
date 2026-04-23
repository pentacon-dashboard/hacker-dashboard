"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

// stub 미확인 알림 수
const STUB_UNREAD = 3;

/**
 * NotificationBell — 헤더 알림 벨 + 빨간 배지 + Popover.
 * - 클릭 시 Popover (빈 상태 "알림 없음")
 * - stub unread=3
 * TODO: GET /notifications 연동 후 실제 알림 목록으로 교체
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

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

  return (
    <div className="relative" data-testid="notification-bell">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`알림 ${STUB_UNREAD}개 미확인`}
        className={cn(
          "relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
          "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <Bell className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        {STUB_UNREAD > 0 && (
          <span
            className="absolute right-0.5 top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-500 text-[8px] font-bold text-white"
            aria-hidden="true"
          >
            {STUB_UNREAD}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-label="알림"
          className={cn(
            "absolute right-0 top-full z-50 mt-1.5 w-72 rounded-2xl border border-border bg-popover shadow-lg",
            "animate-in fade-in duration-200",
          )}
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-semibold text-foreground">알림</span>
            {STUB_UNREAD > 0 && (
              <span className="rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-bold text-red-400">
                {STUB_UNREAD}개 미확인
              </span>
            )}
          </div>
          {/* 빈 상태 */}
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-8 text-center">
            <Bell className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">알림 없음</p>
            <p className="text-xs text-muted-foreground/60">새 알림이 오면 여기에 표시됩니다.</p>
          </div>
        </div>
      )}
    </div>
  );
}
