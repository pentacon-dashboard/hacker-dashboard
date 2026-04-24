import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationBell } from "./notification-bell";

// getNotifications API 모킹
vi.mock("@/lib/api/notifications", () => ({
  getNotifications: vi.fn().mockResolvedValue([
    {
      id: "price-1",
      title: "KRW-BTC 가격 돌파",
      message: "현재가 50,000,000 — 설정 임계가 48,000,000 돌파",
      severity: "critical",
      category: "price",
      unread: true,
      created_at: new Date(Date.now() - 60_000).toISOString(),
    },
    {
      id: "price-2",
      title: "AAPL 가격 하회",
      message: "현재가 170.00 — 설정 임계가 175.00 하회",
      severity: "warning",
      category: "price",
      unread: true,
      created_at: new Date(Date.now() - 7_200_000).toISOString(),
    },
    {
      id: "portfolio-3",
      title: "포트폴리오 일간 상승 3.5%",
      message: "전일 대비 +3.50%",
      severity: "warning",
      category: "portfolio",
      unread: false,
      created_at: new Date(Date.now() - 18_000_000).toISOString(),
    },
  ]),
  markAllRead: vi.fn().mockResolvedValue({ marked_count: 3 }),
  markRead: vi.fn().mockResolvedValue({ id: "price-1", unread: false }),
}));

// useLocale 모킹 — 한국어 고정
vi.mock("@/lib/i18n/locale-provider", () => ({
  useLocale: () => ({
    locale: "ko",
    t: (key: string, vars?: Record<string, string | number>) => {
      const map: Record<string, string> = {
        "header.notifications": "알림",
        "header.notificationsUnread": `${vars?.n ?? 0}개 미확인`,
        "header.markAllRead": "모두 읽음 처리",
        "header.noNotifications": "알림 없음",
      };
      return map[key] ?? key;
    },
  }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("벨 버튼이 렌더된다", async () => {
    render(<NotificationBell />, { wrapper });
    expect(await screen.findByRole("button", { name: /알림/ })).toBeInTheDocument();
  });

  it("클릭 시 팝오버가 열린다", async () => {
    render(<NotificationBell />, { wrapper });
    const btn = await screen.findByRole("button", { name: /알림/ });
    fireEvent.click(btn);
    expect(screen.getByRole("dialog", { name: "알림" })).toBeInTheDocument();
  });

  it("BE 알림 목록이 렌더된다", async () => {
    render(<NotificationBell />, { wrapper });
    fireEvent.click(await screen.findByRole("button", { name: /알림/ }));
    expect(await screen.findByText("KRW-BTC 가격 돌파")).toBeInTheDocument();
    expect(screen.getByText("AAPL 가격 하회")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오 일간 상승 3.5%")).toBeInTheDocument();
  });

  it("배지 숫자가 unread_count 와 일치한다", async () => {
    render(<NotificationBell />, { wrapper });
    // unread: true 인 항목은 2개
    const badge = await screen.findByTestId("notification-badge");
    expect(badge).toHaveTextContent("2");
  });

  it("'모두 읽음 처리' 버튼이 존재한다", async () => {
    render(<NotificationBell />, { wrapper });
    fireEvent.click(await screen.findByRole("button", { name: /알림/ }));
    expect(await screen.findByText("모두 읽음 처리")).toBeInTheDocument();
  });

  it("알림이 없을 때 빈 상태 텍스트를 표시한다", async () => {
    const { getNotifications: mockGetNotifications } = await import("@/lib/api/notifications");
    vi.mocked(mockGetNotifications).mockResolvedValueOnce([]);

    render(<NotificationBell />, { wrapper });
    fireEvent.click(await screen.findByRole("button", { name: /알림/ }));
    expect(await screen.findByText("알림 없음")).toBeInTheDocument();
  });
});
