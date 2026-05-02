import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/helpers/render-with-providers";
import { CsvUploadButton } from "./csv-upload-button";

describe("CsvUploadButton", () => {
  it("renders the CSV upload label", () => {
    renderWithProviders(<CsvUploadButton />);
    expect(screen.getByText("CSV 업로드")).toBeInTheDocument();
  });

  it("links to the upload route", () => {
    renderWithProviders(<CsvUploadButton />);
    expect(screen.getByRole("link", { name: /CSV 파일 업로드/ })).toHaveAttribute(
      "href",
      "/upload",
    );
  });

  it("uses the stable test id", () => {
    renderWithProviders(<CsvUploadButton />);
    expect(screen.getByTestId("csv-upload-button")).toBeInTheDocument();
  });
});
