import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { Sidebar } from "./sidebar";

let mockedPathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => mockedPathname,
  useRouter: () => ({ push: vi.fn() }),
}));

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
  it("renders all primary nav items", () => {
    mockedPathname = "/";
    renderWithProviders(<Sidebar />);
    const navLabels = [
      "고객장부",
      "시장 분석",
      "종목 분석",
      "업로드 & 분석",
      "코파일럿",
      "설정",
    ];

    for (const label of navLabels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.queryByText("워치리스트")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "대시보드" })).not.toBeInTheDocument();
  });

  it("renders the Hacker Dashboard logo", () => {
    mockedPathname = "/";
    renderWithProviders(<Sidebar />);
    expect(screen.getByText("HACKER")).toBeInTheDocument();
  });

  it("renders the demo user card", () => {
    mockedPathname = "/";
    renderWithProviders(<Sidebar />);
    expect(screen.getByText("Demo User")).toBeInTheDocument();
  });

  it("renders the market status card", () => {
    mockedPathname = "/";
    renderWithProviders(<Sidebar />);
    expect(screen.getByText("시장 상태")).toBeInTheDocument();
  });

  it("marks the client book link as current at the root route", () => {
    mockedPathname = "/";
    renderWithProviders(<Sidebar />);
    const clientBookLink = screen.getAllByRole("link", { name: "고객장부" })[0];
    expect(clientBookLink).toHaveAttribute("aria-current", "page");
  });

  it("marks the client book link as current on client workspace routes", () => {
    mockedPathname = "/clients/client-001";
    renderWithProviders(<Sidebar />);
    const clientBookLink = screen.getAllByRole("link", { name: "고객장부" })[0];
    expect(clientBookLink).toHaveAttribute("aria-current", "page");
  });
});
