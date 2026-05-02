import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { ArtifactPanel, ArtifactRail } from "./artifact-panel";

describe("ArtifactPanel", () => {
  const summary = { citations: 3, charts: 1, data: 2, actions: 4 };

  it("keeps artifacts in a thin rail until the user opens the panel", () => {
    const onOpen = vi.fn();
    renderWithProviders(<ArtifactRail summary={summary} onOpen={onOpen} />);

    expect(screen.getByTestId("artifact-rail")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("artifact-rail-citations"));
    expect(onOpen).toHaveBeenCalledWith("citations");
  });

  it("renders evidence, chart, data, and action tabs in the opened panel", () => {
    renderWithProviders(
      <ArtifactPanel summary={summary} activeTab="citations" onTabChange={vi.fn()} onClose={vi.fn()} />,
    );

    expect(screen.getByTestId("artifact-panel")).toBeInTheDocument();
    expect(screen.getByTestId("artifact-tab-citations")).toHaveTextContent("근거");
    expect(screen.getByTestId("artifact-tab-charts")).toHaveTextContent("차트");
    expect(screen.getByTestId("artifact-tab-data")).toHaveTextContent("데이터");
    expect(screen.getByTestId("artifact-tab-actions")).toHaveTextContent("액션");
  });
});
