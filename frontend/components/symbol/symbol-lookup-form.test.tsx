import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithLocale as render } from "@/lib/test-utils";
import { SymbolLookupForm } from "./symbol-lookup-form";
import { searchSymbols, type SymbolInfo } from "@/lib/api/symbols";

const nav = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => nav,
}));

vi.mock("@/lib/api/symbols", () => ({
  searchSymbols: vi.fn(),
}));

const SAMSUNG: SymbolInfo = {
  symbol: "005930",
  name: "삼성전자",
  asset_class: "stock",
  exchange: "KRX",
  market: "naver_kr",
  currency: "KRW",
};

describe("SymbolLookupForm", () => {
  beforeEach(() => {
    nav.push.mockReset();
    vi.mocked(searchSymbols).mockReset();
  });

  it("shows live mapping results from integrated symbol search", async () => {
    vi.mocked(searchSymbols).mockResolvedValue([SAMSUNG]);
    render(<SymbolLookupForm />);

    fireEvent.change(screen.getByRole("searchbox", { name: "종목 검색" }), {
      target: { value: "삼성전자" },
    });

    await waitFor(() => {
      expect(searchSymbols).toHaveBeenCalledWith("삼성전자");
    });
    expect(await screen.findByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText(/005930/)).toBeInTheDocument();
    expect(screen.getByText(/naver_kr/)).toBeInTheDocument();
  });

  it("routes Enter to the first mapped result instead of yahoo fallback", async () => {
    vi.mocked(searchSymbols).mockResolvedValue([SAMSUNG]);
    render(<SymbolLookupForm />);

    fireEvent.change(screen.getByRole("searchbox", { name: "종목 검색" }), {
      target: { value: "삼성전자" },
    });
    await waitFor(() => {
      expect(searchSymbols).toHaveBeenCalledWith("삼성전자");
    });
    await screen.findByText("삼성전자");

    fireEvent.submit(screen.getByTestId("symbol-lookup-form"));

    await waitFor(() => {
      expect(nav.push).toHaveBeenCalledWith("/symbol/naver_kr/005930");
    });
  });

  it("routes keyboard Enter from the input to the first mapped result", async () => {
    vi.mocked(searchSymbols).mockResolvedValue([SAMSUNG]);
    render(<SymbolLookupForm />);

    const input = screen.getByRole("searchbox", { name: "종목 검색" });
    fireEvent.change(input, {
      target: { value: "삼성전자" },
    });
    await waitFor(() => {
      expect(searchSymbols).toHaveBeenCalledWith("삼성전자");
    });
    await screen.findByText("삼성전자");

    fireEvent.keyDown(input, { key: "Enter", code: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(nav.push).toHaveBeenCalledWith("/symbol/naver_kr/005930");
    });
  });

  it("routes the visible submit button to the first mapped result", async () => {
    vi.mocked(searchSymbols).mockResolvedValue([SAMSUNG]);
    render(<SymbolLookupForm />);

    fireEvent.change(screen.getByRole("searchbox", { name: "종목 검색" }), {
      target: { value: "삼성전자" },
    });
    await waitFor(() => {
      expect(searchSymbols).toHaveBeenCalledWith("삼성전자");
    });
    await screen.findByText("삼성전자");

    fireEvent.click(within(screen.getByTestId("symbol-lookup-form")).getByRole("button"));

    await waitFor(() => {
      expect(nav.push).toHaveBeenCalledWith("/symbol/naver_kr/005930");
    });
  });

  it("falls back to deterministic routing when no mapping result exists", async () => {
    vi.mocked(searchSymbols).mockResolvedValue([]);
    render(<SymbolLookupForm />);

    fireEvent.change(screen.getByRole("searchbox", { name: "종목 검색" }), {
      target: { value: "005930" },
    });
    fireEvent.submit(screen.getByTestId("symbol-lookup-form"));

    await waitFor(() => {
      expect(nav.push).toHaveBeenCalledWith("/symbol/naver_kr/005930");
    });
  });
});
