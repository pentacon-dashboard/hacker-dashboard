"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui";
import { Sheet } from "@/components/ui/sheet";

import {
  LayoutDashboard,
  Eye,
  Briefcase,
  LineChart as LineChartIcon,
  Newspaper,
  Settings,
} from "lucide-react";

const ICON_CLASS = "h-[18px] w-[18px]";

const navItems = [
  {
    href: "/",
    label: "대시보드",
    icon: <LayoutDashboard className={ICON_CLASS} aria-hidden="true" />,
  },
  {
    href: "/watchlist",
    label: "워치리스트",
    icon: <Eye className={ICON_CLASS} aria-hidden="true" />,
  },
  {
    href: "/portfolio",
    label: "포트폴리오",
    icon: <Briefcase className={ICON_CLASS} aria-hidden="true" />,
  },
  {
    href: "/analyze",
    label: "분석",
    icon: <LineChartIcon className={ICON_CLASS} aria-hidden="true" />,
  },
  {
    href: "/news",
    label: "뉴스",
    icon: <Newspaper className={ICON_CLASS} aria-hidden="true" />,
  },
  {
    href: "/settings",
    label: "설정",
    icon: <Settings className={ICON_CLASS} aria-hidden="true" />,
  },
];

function NavContent({
  collapsed,
  onLinkClick,
}: {
  collapsed: boolean;
  onLinkClick?: () => void;
}) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-1 px-2 py-2" aria-label="메인 내비게이션">
      {navItems.map((item) => {
        const isActive =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onLinkClick}
            className={cn(
              "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
              "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground",
            )}
            aria-current={isActive ? "page" : undefined}
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } =
    useUiStore();

  return (
    <>
      {/* 모바일 Drawer (<md) — 햄버거 버튼은 Header 에 배치, 여기서는 Sheet 만 관리 */}
      <Sheet open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} side="left">
        <div className="flex h-full flex-col">
          <div className="flex h-14 items-center justify-between px-3">
            <span className="text-sm font-semibold tracking-tight">
              Hacker Dashboard
            </span>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="rounded p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="메뉴 닫기"
              type="button"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="18" x2="6" y1="6" y2="18" />
                <line x1="6" x2="18" y1="6" y2="18" />
              </svg>
            </button>
          </div>
          <NavContent collapsed={false} onLinkClick={() => setMobileMenuOpen(false)} />
        </div>
      </Sheet>

      {/* 데스크탑 사이드바 (md 이상) */}
      <aside
        className={cn(
          "hidden h-full flex-col border-r bg-background transition-all duration-200 md:flex",
          sidebarCollapsed ? "w-16" : "w-56",
        )}
        aria-label="메인 내비게이션"
      >
        <div className="flex h-14 items-center justify-between px-3">
          {!sidebarCollapsed && (
            <span className="text-sm font-semibold tracking-tight">
              Hacker Dashboard
            </span>
          )}
          <button
            onClick={toggleSidebar}
            className="ml-auto rounded p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={sidebarCollapsed ? "사이드바 펼치기" : "사이드바 접기"}
            type="button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              {sidebarCollapsed ? (
                <path d="m9 18 6-6-6-6" />
              ) : (
                <path d="m15 18-6-6 6-6" />
              )}
            </svg>
          </button>
        </div>

        <NavContent collapsed={sidebarCollapsed} />
      </aside>
    </>
  );
}
