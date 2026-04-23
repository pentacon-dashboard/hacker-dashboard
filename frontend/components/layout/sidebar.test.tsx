import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "./sidebar";

// next/navigation mock
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));

// zustand store mock — 기본 상태
vi.mock("@/stores/ui", () => ({
  useUiStore: (selector?: (s: object) => unknown) => {
    const state = {
      sidebarCollapsed: false,
      toggleSidebar: vi.fn(),
      mobileMenuOpen: false,
      setMobileMenuOpen: vi.fn(),
      toggleMobileMenu: vi.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

describe("Sidebar", () => {
  it("8개 nav 항목이 모두 렌더된다", () => {
    render(<Sidebar />);
    const navLabels = [
      "대시보드",
      "포트폴리오",
      "워치리스트",
      "종목 분석",
      "시장 분석",
      "코파일럿",
      "업로드 & 분석",
      "설정",
    ];
    for (const label of navLabels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("LogoBadge HACKER 텍스트가 렌더된다", () => {
    render(<Sidebar />);
    expect(screen.getByText("HACKER")).toBeInTheDocument();
  });

  it("SidebarUserCard Demo User 텍스트가 렌더된다", () => {
    render(<Sidebar />);
    expect(screen.getByText("Demo User")).toBeInTheDocument();
  });

  it("MarketStatusCard '시장 상태' 텍스트가 렌더된다", () => {
    render(<Sidebar />);
    expect(screen.getByText("시장 상태")).toBeInTheDocument();
  });

  it("대시보드 링크에 aria-current='page'가 적용된다 (pathname='/')", () => {
    render(<Sidebar />);
    const dashLink = screen.getAllByRole("link", { name: "대시보드" })[0];
    expect(dashLink).toHaveAttribute("aria-current", "page");
  });
});
