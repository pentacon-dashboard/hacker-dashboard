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

  it("renders ambiguous client candidates and selects only the clicked client id", () => {
    const onClientCandidateSelect = vi.fn();

    renderWithProviders(
      <ThreadView
        sessionId="s1"
        messages={[
          {
            role: "assistant",
            content: "일치하는 고객이 여러 명입니다. 고객을 선택해 주세요.",
            card: {
              type: "text",
              content: "일치하는 고객이 여러 명입니다. 고객을 선택해 주세요.",
              degraded: true,
              client_resolution_status: "ambiguous",
              requires_client_selection: true,
              client_candidates: [
                {
                  client_id: "client-007",
                  display_label: "김민수",
                  holdings_count: 4,
                  last_activity_at: "2026-05-01T09:00:00",
                },
                {
                  client_id: "client-003",
                  display_label: "김민수",
                  holdings_count: 1,
                  last_activity_at: "2026-04-01T09:00:00",
                },
              ],
            },
          },
        ]}
        streamState={initialCopilotState}
        onSendMessage={vi.fn()}
        onClientCandidateSelect={onClientCandidateSelect}
      />,
    );

    expect(screen.getByTestId("client-candidate-list")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("client-candidate-client-007"));

    expect(onClientCandidateSelect).toHaveBeenCalledWith("client-007");
    expect(onClientCandidateSelect).toHaveBeenCalledTimes(1);
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
