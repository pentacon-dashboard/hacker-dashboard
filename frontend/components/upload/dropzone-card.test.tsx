import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/lib/i18n/locale-provider";
import { DropzoneCard } from "./dropzone-card";

function renderDropzone(onFileAccepted = vi.fn()) {
  render(
    <LocaleProvider>
      <DropzoneCard onFileAccepted={onFileAccepted} />
    </LocaleProvider>,
  );
  return { onFileAccepted };
}

describe("DropzoneCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("exposes a real file select button", () => {
    renderDropzone();

    const button = screen.getByTestId("file-select-button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveAccessibleName("파일 선택");
    expect(button).not.toHaveAttribute("aria-hidden", "true");
    expect(button).not.toHaveAttribute("tabindex", "-1");
  });

  it("opens the native file picker from the select button", () => {
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    renderDropzone();

    fireEvent.click(screen.getByTestId("file-select-button"));

    expect(clickSpy).toHaveBeenCalled();
  });

  it("accepts a CSV selected from the native file input", async () => {
    const onFileAccepted = vi.fn();
    renderDropzone(onFileAccepted);

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = new File(["date,market,code,quantity,avg_cost,currency\n2026-04-25,NASDAQ,AAPL,1,180,USD"], "portfolio.csv", {
      type: "text/csv",
    });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(onFileAccepted).toHaveBeenCalledWith(file));
  });
});
