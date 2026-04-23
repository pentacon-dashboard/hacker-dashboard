import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NotificationBell } from "./notification-bell";

describe("NotificationBell", () => {
  it("벨 버튼이 렌더된다", () => {
    render(<NotificationBell />);
    expect(screen.getByRole("button", { name: /알림/ })).toBeInTheDocument();
  });

  it("클릭 시 팝오버가 열린다", () => {
    render(<NotificationBell />);
    const btn = screen.getByRole("button", { name: /알림/ });
    fireEvent.click(btn);
    expect(screen.getByRole("dialog", { name: "알림" })).toBeInTheDocument();
  });

  it("팝오버에 stub 알림 3건이 렌더된다", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /알림/ }));
    expect(screen.getByText("KRW-BTC 가격 +5% 돌파")).toBeInTheDocument();
    expect(screen.getByText("AAPL 실적 발표 임박 (4/28)")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오 일간 변동 +3% 초과")).toBeInTheDocument();
  });

  it("배지 숫자와 팝오버 미확인 수가 일치한다", () => {
    render(<NotificationBell />);
    // 배지에 "3" 표시
    expect(screen.getByText("3")).toBeInTheDocument();
    // 팝오버 열기
    fireEvent.click(screen.getByRole("button", { name: /알림/ }));
    expect(screen.getByText("3개 미확인")).toBeInTheDocument();
  });

  it("'모두 읽음 처리' 클릭 시 배지가 사라진다", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /알림/ }));
    fireEvent.click(screen.getByText("모두 읽음 처리"));
    expect(screen.queryByText("3")).not.toBeInTheDocument();
    expect(screen.queryByText("3개 미확인")).not.toBeInTheDocument();
  });
});
