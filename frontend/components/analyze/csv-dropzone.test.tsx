import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CsvDropzone } from "./csv-dropzone";

vi.mock("@/lib/api/analyze", () => ({
  analyzeCsv: vi.fn(),
}));

describe("CsvDropzone", () => {
  const onResult = vi.fn();
  const onError = vi.fn();

  beforeEach(() => {
    onResult.mockClear();
    onError.mockClear();
  });

  it("renders with correct data-testid", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);
    expect(screen.getByTestId("csv-dropzone")).toBeInTheDocument();
  });

  it("submit button is disabled when no file selected", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);
    const submitBtn = screen.getByTestId("csv-submit");
    expect(submitBtn).toBeDisabled();
  });

  it("shows file name label after selecting a valid CSV file", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["col1,col2\n1,2"], "test.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByTestId("csv-file-label")).toBeInTheDocument();
    expect(screen.getByTestId("csv-file-label")).toHaveTextContent("test.csv");
  });

  it("shows error message for oversized file", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    // 11MB 파일 시뮬레이션
    const bigContent = "a".repeat(11 * 1024 * 1024);
    const bigFile = new File([bigContent], "big.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [bigFile] } });

    const errorEl = screen.getByTestId("csv-file-error");
    expect(errorEl).toBeInTheDocument();
    expect(errorEl).toHaveTextContent("10MB");
  });

  it("shows error message for non-CSV file", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const txtFile = new File(["hello"], "data.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [txtFile] } });

    const errorEl = screen.getByTestId("csv-file-error");
    expect(errorEl).toBeInTheDocument();
    expect(errorEl).toHaveTextContent("CSV");
  });

  it("submit button is enabled after selecting a valid file", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["col1,col2\n1,2"], "test.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [file] } });

    const submitBtn = screen.getByTestId("csv-submit");
    expect(submitBtn).not.toBeDisabled();
  });

  it("submit button remains disabled when file has size error", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const bigContent = "a".repeat(11 * 1024 * 1024);
    const bigFile = new File([bigContent], "big.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [bigFile] } });

    const submitBtn = screen.getByTestId("csv-submit");
    expect(submitBtn).toBeDisabled();
  });

  it("drag over changes visual state via class", () => {
    render(<CsvDropzone onResult={onResult} onError={onError} />);
    const dropzone = screen.getByTestId("csv-dropzone");
    const dropArea = dropzone.querySelector('[role="button"]') as HTMLElement;

    fireEvent.dragOver(dropArea, { dataTransfer: { files: [] } });
    // isDragging=true 시 bg-primary/5 클래스가 추가됨
    expect(dropArea.className).toContain("bg-primary/5");

    fireEvent.dragLeave(dropArea);
    // isDragging=false 시 bg-primary/5 가 제거되고 hover:bg-muted/40 이 표시됨
    expect(dropArea.className).not.toContain("bg-primary/5");
  });
});
