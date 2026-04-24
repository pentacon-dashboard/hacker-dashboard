"use client";

import { cn } from "@/lib/utils";

// TODO: GET /users/me 연동 후 실제 사용자 정보로 교체
const STUB_USER = {
  name: "Demo User",
  email: "demo@demo.com",
  initial: "D",
} as const;

interface SidebarUserCardProps {
  collapsed?: boolean;
}

/**
 * 사이드바 하단 Demo User 프로필 카드.
 * - 펼침: 아바타(원형, 이니셜) + 이름 + 이메일
 * - 접힘: 아바타만 표시
 */
export function SidebarUserCard({ collapsed = false }: SidebarUserCardProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-xl border border-border/50 bg-card/50 px-2 py-2",
        collapsed ? "justify-center" : "px-2.5",
      )}
      aria-label={`사용자: ${STUB_USER.name}`}
    >
      {/* 아바타 */}
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground"
        aria-hidden="true"
      >
        {STUB_USER.initial}
      </div>

      {/* 이름/이메일 (펼침 상태에서만) */}
      {!collapsed && (
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-foreground leading-tight">
            {STUB_USER.name}
          </p>
          <p className="truncate text-[10px] text-muted-foreground leading-tight">
            {STUB_USER.email}
          </p>
        </div>
      )}
    </div>
  );
}
