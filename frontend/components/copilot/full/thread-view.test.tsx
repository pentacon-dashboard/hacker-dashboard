import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { initialCopilotState } from "@/hooks/use-copilot-stream";
import { ThreadView } from "./thread-view";

describe("ThreadView", () => {
  it("renders user bubbles, assistant body text, artifact chips, and a multiline composer", () => {
    const onSendMessage = vi.fn();

    renderWithProviders(
      <ThreadView
        sessionId="s1"
        messages={[
          { role: "user", content: "방금 비중을 쉽게 설명해줘" },
          {
            role: "assistant",
            content: "검증된 이전 답변을 고객용 문장으로 정리했습니다.",
            artifacts: { citations: 3, charts: 1, actions: 4 },
          },
        ]}
        streamState={initialCopilotState}
        onSendMessage={onSendMessage}
        onArtifactSelect={vi.fn()}
      />,
    );

    expect(screen.getByTestId("thread-composer")).toHaveAttribute("data-multiline", "true");
    expect(screen.getByTestId("message-user-0")).toHaveClass("justify-end");
    expect(screen.getByTestId("message-assistant-1")).toHaveClass("justify-start");
    expect(screen.getByTestId("artifact-chip-citations")).toHaveTextContent("근거 3");
    expect(screen.getByTestId("artifact-chip-charts")).toHaveTextContent("차트 1");
    expect(screen.getByTestId("artifact-chip-actions")).toHaveTextContent("리밸런싱 4");
  });

  it("submits the textarea content and clears the composer", () => {
    const onSendMessage = vi.fn();

    renderWithProviders(
      <ThreadView
        sessionId="s1"
        messages={[]}
        streamState={initialCopilotState}
        onSendMessage={onSendMessage}
      />,
    );

    const textarea = screen.getByTestId("thread-input") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "요약해줘" } });
    fireEvent.submit(screen.getByTestId("thread-composer"));

    expect(onSendMessage).toHaveBeenCalledWith("요약해줘");
    expect(textarea.value).toBe("");
  });

  it("shows a typing skeleton while the stream is running and hides raw gate details", () => {
    renderWithProviders(
      <ThreadView
        sessionId="s1"
        messages={[]}
        streamState={{
          ...initialCopilotState,
          status: "streaming",
          steps: {
            a: {
              buffer: "",
              card: null,
              degraded: false,
              gates: { schema: "pass", domain: "pass", critique: "pass" },
            },
          },
        }}
        onSendMessage={vi.fn()}
      />,
    );

    expect(screen.getByTestId("assistant-typing")).toBeInTheDocument();
    expect(screen.queryByText(/schema|domain|critique|step_id/i)).not.toBeInTheDocument();
  });
});
