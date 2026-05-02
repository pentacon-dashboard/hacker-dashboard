import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { SessionSidebar } from "./session-sidebar";

const sessions = [
  {
    session_id: "s1",
    title: "NVDA 고객 설명",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    turn_count: 2,
    last_query: "방금 답을 쉽게 설명해줘",
  },
];

describe("SessionSidebar", () => {
  it("can render in collapsed mode with only the new chat and toggle controls", () => {
    renderWithProviders(
      <SessionSidebar
        sessions={sessions}
        activeSessionId="s1"
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        collapsed
        onToggleCollapsed={vi.fn()}
      />,
    );

    expect(screen.getByTestId("session-sidebar")).toHaveAttribute("data-collapsed", "true");
    expect(screen.getByTestId("new-session-btn")).toBeInTheDocument();
    expect(screen.queryByText("NVDA 고객 설명")).not.toBeInTheDocument();
  });

  it("calls the collapse toggle from the desktop sidebar control", () => {
    const onToggleCollapsed = vi.fn();
    renderWithProviders(
      <SessionSidebar
        sessions={sessions}
        activeSessionId={null}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        onToggleCollapsed={onToggleCollapsed}
      />,
    );

    fireEvent.click(screen.getByTestId("sidebar-collapse-btn"));

    expect(onToggleCollapsed).toHaveBeenCalled();
  });
});
