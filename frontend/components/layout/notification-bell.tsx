"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Info, AlertTriangle, AlertOctagon } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";
import {
  getNotifications,
  markAllRead,
  type Notification,
} from "@/lib/api/notifications";

// severity → 아이콘 + 색상 매핑
function SeverityIcon({ severity }: { severity: Notification["severity"] }) {
  if (severity === "critical") {
    return <AlertOctagon className="h-3.5 w-3.5 shrink-0 text-red-500 mt-0.5" aria-hidden="true" />;
  }
  if (severity === "warning") {
    return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400 mt-0.5" aria-hidden="true" />;
  }
  return <Info className="h-3.5 w-3.5 shrink-0 text-blue-400 mt-0.5" aria-hidden="true" />;
}

/** ISO 타임스탬프를 상대 시간 문자열로 변환 (예: "3분 전") */
function relativeTime(isoString: string): string {
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60_000);
    if (minutes < 1) return "방금 전";
    if (minutes < 60) return `${minutes}분 전`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}시간 전`;
    const days = Math.floor(hours / 24);
    return `${days}일 전`;
  } catch {
    return "";
  }
}

/**
 * NotificationBell — 헤더 알림 벨 + 빨간 배지 + Popover.
 * - GET /notifications (TanStack Query) 로 실 BE 데이터 렌더
 * - severity 별 아이콘 색 (info=blue, warning=amber, critical=red)
 * - "모두 읽음 처리" → POST /notifications/read-all + 쿼리 무효화
 */
export function NotificationBell() {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();

  // BE 알림 목록 조회
  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => getNotifications(10),
    // 30초마다 자동 갱신
    refetchInterval: 30_000,
    // 팝오버가 열린 상태에서 포커스 복귀 시 재조회
    refetchOnWindowFocus: true,
  });

  const unreadCount = notifications.filter((n) => n.unread).length;

  // 전체 읽음 처리 mutation
  const markAllMutation = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      // 서버가 읽음 처리했으니 로컬 캐시도 무효화해서 재조회
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  // 바깥 클릭 → 팝오버 닫기
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
        aria-label={
          unreadCount > 0
            ? t("header.notificationsUnread", { n: unreadCount })
            : t("header.notifications")
        }
        className={cn(
          "relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
          "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <Bell className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        {unreadCount > 0 && (
          <span
            data-testid="notification-badge"
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
          aria-label={t("header.notifications")}
          className={cn(
            "absolute right-0 top-full z-50 mt-1.5 w-80 rounded-2xl border border-border bg-popover shadow-lg",
            "animate-in fade-in duration-200",
          )}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-semibold text-foreground">
              {t("header.notifications")}
            </span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-bold text-red-400">
                {t("header.notificationsUnread", { n: unreadCount })}
              </span>
            )}
          </div>

          {/* 알림 리스트 */}
          {notifications.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">
              {t("header.noNotifications")}
            </div>
          ) : (
            <ul
              className="max-h-72 overflow-y-auto divide-y divide-border"
              role="list"
            >
              {notifications.map((notification) => (
                <li
                  key={notification.id}
                  className={cn(
                    "flex items-start gap-3 px-4 py-3 transition-colors",
                    notification.unread && "bg-muted/30",
                  )}
                >
                  <SeverityIcon severity={notification.severity} />
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-sm leading-snug",
                        notification.unread
                          ? "font-medium text-foreground"
                          : "text-muted-foreground",
                      )}
                    >
                      {notification.title}
                    </p>
                    {notification.message && (
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                        {notification.message}
                      </p>
                    )}
                    <p className="mt-0.5 text-[10px] text-muted-foreground">
                      {relativeTime(notification.created_at)}
                    </p>
                  </div>
                  {notification.unread && (
                    <span
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500"
                      aria-label="미확인"
                    />
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* 모두 읽음 처리 */}
          <div className="border-t border-border px-4 py-2.5">
            <button
              type="button"
              disabled={markAllMutation.isPending || unreadCount === 0}
              onClick={() => markAllMutation.mutate()}
              className={cn(
                "w-full text-center text-xs transition-colors",
                unreadCount > 0
                  ? "text-muted-foreground hover:text-foreground"
                  : "text-muted-foreground/40 cursor-not-allowed",
              )}
            >
              {t("header.markAllRead")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
