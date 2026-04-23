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

  it("팝오버에서 '알림 없음' 텍스트를 렌더한다", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /알림/ }));
    expect(screen.getByText("알림 없음")).toBeInTheDocument();
  });
});
