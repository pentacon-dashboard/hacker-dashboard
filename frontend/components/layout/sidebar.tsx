"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui";
import { Sheet } from "@/components/ui/sheet";
import { LogoBadge } from "@/components/layout/logo-badge";
import { SidebarUserCard } from "@/components/layout/sidebar-user-card";
import { MarketStatusCard } from "@/components/layout/market-status-card";
import { useLocale } from "@/lib/i18n/locale-provider";

import {
  LayoutDashboard,
  Briefcase,
  Eye,
  LineChart,
  Globe,
  Sparkles,
  Upload,
  Settings,
} from "lucide-react";

const ICON_CLASS = "h-[18px] w-[18px] shrink-0";

const navItems = [
  { href: "/", labelKey: "sidebar.dashboard", icon: <LayoutDashboard className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/portfolio", labelKey: "sidebar.portfolio", icon: <Briefcase className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/watchlist", labelKey: "sidebar.watchlist", icon: <Eye className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/symbol", labelKey: "sidebar.symbol", icon: <LineChart className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/market-analyze", labelKey: "sidebar.market", icon: <Globe className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/copilot", labelKey: "sidebar.copilot", icon: <Sparkles className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/upload", labelKey: "sidebar.upload", icon: <Upload className={ICON_CLASS} aria-hidden="true" /> },
  { href: "/settings", labelKey: "sidebar.settings", icon: <Settings className={ICON_CLASS} aria-hidden="true" /> },
];

function NavContent({
  collapsed,
  onLinkClick,
}: {
  collapsed: boolean;
  onLinkClick?: () => void;
}) {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav className="flex-1 space-y-0.5 px-2 py-2" aria-label={t("sidebar.dashboard")}>
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
              "flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors",
              "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isActive
                ? "bg-primary/15 text-primary dark:bg-primary/20 dark:text-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
            aria-current={isActive ? "page" : undefined}
          >
            {item.icon}
            {!collapsed && <span className="truncate">{t(item.labelKey)}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } =
    useUiStore();
  const { t } = useLocale();

  return (
    <>
      {/* 모바일 Drawer (<md) — 햄버거 버튼은 Header 에 배치, 여기서는 Sheet 만 관리 */}
      <Sheet open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} side="left">
        <div className="flex h-full flex-col">
          {/* 모바일 드로어 헤더 */}
          <div className="flex h-14 items-center justify-between px-3">
            <LogoBadge collapsed={false} />
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="rounded-lg p-1.5 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
          {/* 모바일 하단 카드 */}
          <div className="px-2 pb-3 space-y-2">
            <SidebarUserCard collapsed={false} />
            <MarketStatusCard collapsed={false} />
          </div>
        </div>
      </Sheet>

      {/* 데스크탑 사이드바 (md 이상) */}
      <aside
        className={cn(
          "hidden h-full flex-col border-r border-border/50 bg-background transition-all duration-200 md:flex",
          sidebarCollapsed ? "w-16" : "w-56",
        )}
        aria-label="메인 내비게이션"
      >
        {/* 로고 배지 영역 */}
        <div
          className={cn(
            "flex h-14 items-center border-b border-border/50",
            sidebarCollapsed ? "justify-center px-1" : "justify-between px-3",
          )}
        >
          <LogoBadge collapsed={sidebarCollapsed} />
          <button
            onClick={toggleSidebar}
            className={cn(
              "rounded-lg p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              sidebarCollapsed && "hidden",
            )}
            aria-label={sidebarCollapsed ? t("sidebar.expand") : t("sidebar.collapse")}
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
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>
          {sidebarCollapsed && (
            <button
              onClick={toggleSidebar}
              className="rounded-lg p-1 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="사이드바 펼치기"
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
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          )}
        </div>

        <NavContent collapsed={sidebarCollapsed} />

        {/* 사이드바 하단 — 유저카드 + 시장 상태 (mt-auto로 하단 고정) */}
        <div className="mt-auto px-2 pb-3 space-y-2">
          <SidebarUserCard collapsed={sidebarCollapsed} />
          <MarketStatusCard collapsed={sidebarCollapsed} />
        </div>
      </aside>
    </>
  );
}
