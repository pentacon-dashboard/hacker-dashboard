import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CsvUploadButton } from "./csv-upload-button";

// next/navigation mock
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("CsvUploadButton", () => {
  it("'CSV 업로드' 텍스트를 렌더한다", () => {
    render(<CsvUploadButton />);
    expect(screen.getByText("CSV 업로드")).toBeInTheDocument();
  });

  it("클릭 시 /upload 로 라우팅한다", () => {
    render(<CsvUploadButton />);
    fireEvent.click(screen.getByRole("button", { name: /CSV 파일 업로드/ }));
    expect(mockPush).toHaveBeenCalledWith("/upload");
  });

  it("data-testid 가 csv-upload-button 이다", () => {
    render(<CsvUploadButton />);
    expect(screen.getByTestId("csv-upload-button")).toBeInTheDocument();
  });
});
