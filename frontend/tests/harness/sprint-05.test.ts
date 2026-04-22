import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import React from "react";
import { TurnHistory } from "@/components/copilot/turn-history";
import { useCopilotSession } from "@/hooks/use-copilot-session";
import { renderHook } from "@testing-library/react";

describe("sprint-05 acceptance — 세션 턴 히스토리 렌더", () => {
  it("SessionTurn 배열을 시간 역순으로 렌더", () => {
    render(
      React.createElement(TurnHistory, {
        turns: [
          {
            turn_id: "t1",
            query: "AAPL 분석",
            plan_id: "p1",
            final_card: { type: "text", body: "요약1" },
            citations: [],
            created_at: "2026-04-22T10:00:00Z",
          },
          {
            turn_id: "t2",
            query: "공시 요약",
            plan_id: "p2",
            final_card: { type: "text", body: "요약2" },
            citations: [],
            created_at: "2026-04-22T10:01:00Z",
          },
        ],
      }),
    );
    const items = screen.getAllByRole("listitem");
    expect(items[0].textContent).toContain("공시 요약");
    expect(items[1].textContent).toContain("AAPL 분석");
  });
});

describe("sprint-05 acceptance — 세션 ID 저장 정책", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("session_id는 sessionStorage에만 저장되고 localStorage에는 저장되지 않는다", () => {
    const { result } = renderHook(() => useCopilotSession());
    act(() => {
      result.current.setSessionId("abc-123");
    });
    expect(sessionStorage.getItem("copilot.session_id")).toBe("abc-123");
    expect(localStorage.getItem("copilot.session_id")).toBeNull();
  });

  it("URL query string에 session_id 노출되지 않음", () => {
    const { result } = renderHook(() => useCopilotSession());
    act(() => {
      result.current.setSessionId("abc-123");
    });
    expect(window.location.search).not.toContain("session_id");
  });

  it("clearSession 호출 시 sessionStorage에서도 삭제된다", () => {
    const { result } = renderHook(() => useCopilotSession());
    act(() => {
      result.current.setSessionId("abc-123");
    });
    expect(sessionStorage.getItem("copilot.session_id")).toBe("abc-123");

    act(() => {
      result.current.clearSession();
    });
    expect(sessionStorage.getItem("copilot.session_id")).toBeNull();
    expect(result.current.sessionId).toBeNull();
  });
});
