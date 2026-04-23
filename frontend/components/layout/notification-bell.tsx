"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

interface StubNotification {
  id: number;
  title: string;
  time: string;
  unread: boolean;
}

const STUB_NOTIFICATIONS: StubNotification[] = [
  { id: 1, title: "KRW-BTC 가격 +5% 돌파", time: "방금 전", unread: true },
  { id: 2, title: "AAPL 실적 발표 임박 (4/28)", time: "2시간 전", unread: true },
  { id: 3, title: "포트폴리오 일간 변동 +3% 초과", time: "5시간 전", unread: true },
];

/**
 * NotificationBell — 헤더 알림 벨 + 빨간 배지 + Popover.
 * - 클릭 시 Popover (stub 알림 3건 리스트)
 * - "모두 읽음 처리" 클릭 시 배지 숨김
 * TODO: GET /notifications 연동 후 실제 알림 목록으로 교체
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(
    STUB_NOTIFICATIONS.filter((n) => n.unread).length,
  );
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
        aria-label={unreadCount > 0 ? `알림 ${unreadCount}개 미확인` : "알림"}
        className={cn(
          "relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
          "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <Bell className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        {unreadCount > 0 && (
          <span
            className="absolute right-0.5 top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-500 text-[8px] font-bold text-white"
            aria-hidden="true"
          >
            {unreadCount}
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
            {unreadCount > 0 && (
              <span className="rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-bold text-red-400">
                {unreadCount}개 미확인
              </span>
            )}
          </div>

          {/* 알림 리스트 */}
          <ul className="divide-y divide-border" role="list">
            {STUB_NOTIFICATIONS.map((notification) => (
              <li
                key={notification.id}
                className="flex items-start gap-3 px-4 py-3"
              >
                {notification.unread ? (
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500"
                    aria-label="미확인"
                  />
                ) : (
                  <span className="mt-1.5 h-2 w-2 shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground leading-snug">
                    {notification.title}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {notification.time}
                  </p>
                </div>
              </li>
            ))}
          </ul>

          {/* 모두 읽음 처리 */}
          <div className="border-t border-border px-4 py-2.5">
            <button
              type="button"
              onClick={() => setUnreadCount(0)}
              className="w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              모두 읽음 처리
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
