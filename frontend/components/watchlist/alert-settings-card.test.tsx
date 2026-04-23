import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AlertSettingsCard } from "./alert-settings-card";
import type { WatchlistAlert } from "@/lib/api/watchlist";

vi.mock("@/lib/api/watchlist", () => ({
  getAlerts: vi.fn(),
  createAlert: vi.fn(),
  updateAlert: vi.fn(),
  deleteAlert: vi.fn(),
}));

import {
  getAlerts,
  createAlert,
  updateAlert,
  deleteAlert,
} from "@/lib/api/watchlist";

const MOCK_ALERTS: WatchlistAlert[] = [
  {
    id: 1,
    user_id: "demo",
    symbol: "NVDA",
    market: "yahoo",
    direction: "above",
    threshold: "550.0000",
    enabled: true,
    created_at: "2026-04-20T00:00:00Z",
  },
  {
    id: 2,
    user_id: "demo",
    symbol: "KRW-BTC",
    market: "upbit",
    direction: "below",
    threshold: "70000000.0000",
    enabled: false,
    created_at: "2026-04-20T00:00:00Z",
  },
];

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AlertSettingsCard", () => {
  it("로딩 중에는 스켈레톤을 렌더한다", async () => {
    vi.mocked(getAlerts).mockReturnValue(new Promise(() => {}));
    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    expect(screen.getByTestId("alert-rules-loading")).toBeInTheDocument();
  });

  it("알림 목록을 정상 렌더한다", async () => {
    vi.mocked(getAlerts).mockResolvedValue(MOCK_ALERTS);
    render(<AlertSettingsCard />, { wrapper: makeWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-list")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("alert-rule-1")).toBeInTheDocument();
    expect(screen.getByTestId("alert-rule-2")).toBeInTheDocument();
    expect(screen.getByText("NVDA")).toBeInTheDocument();
    expect(screen.getByText("KRW-BTC")).toBeInTheDocument();
  });

  it("빈 배열이면 empty state를 렌더한다", async () => {
    vi.mocked(getAlerts).mockResolvedValue([]);
    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-empty")).toBeInTheDocument(),
    );
  });

  it("에러 시 에러 상태를 렌더한다", async () => {
    vi.mocked(getAlerts).mockRejectedValue(new Error("network error"));
    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-error")).toBeInTheDocument(),
    );
  });

  it("+ 추가 클릭 시 인라인 폼이 표시된다", async () => {
    vi.mocked(getAlerts).mockResolvedValue(MOCK_ALERTS);
    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-list")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByLabelText("알림 추가"));
    expect(screen.getByTestId("add-alert-form")).toBeInTheDocument();
  });

  it("폼 submit → createAlert 호출 후 목록 갱신", async () => {
    const newAlert: WatchlistAlert = {
      id: 3,
      user_id: "demo",
      symbol: "AAPL",
      market: "yahoo",
      direction: "above",
      threshold: "260.0000",
      enabled: true,
      created_at: "2026-04-24T00:00:00Z",
    };
    vi.mocked(getAlerts).mockResolvedValue(MOCK_ALERTS);
    vi.mocked(createAlert).mockResolvedValue(newAlert);

    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-list")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByLabelText("알림 추가"));
    await waitFor(() =>
      expect(screen.getByTestId("add-alert-form")).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText("종목 티커"), {
      target: { value: "AAPL" },
    });
    fireEvent.change(screen.getByLabelText("기준가"), {
      target: { value: "260" },
    });

    fireEvent.submit(screen.getByTestId("add-alert-form"));

    await waitFor(() => {
      expect(createAlert).toHaveBeenCalledWith({
        symbol: "AAPL",
        market: "yahoo",
        direction: "above",
        threshold: 260,
      });
    });
  });

  it("updateAlert: 벨 버튼 클릭 시 호출된다", async () => {
    vi.mocked(getAlerts).mockResolvedValue(MOCK_ALERTS);
    vi.mocked(updateAlert).mockResolvedValue({
      ...MOCK_ALERTS[0]!,
      enabled: false,
    });

    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rule-1")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByLabelText("NVDA 알림 끄기"));
    await waitFor(() => {
      expect(updateAlert).toHaveBeenCalledWith(1, { enabled: false });
    });
  });

  it("deleteAlert: 삭제 버튼 클릭 시 호출된다", async () => {
    vi.mocked(getAlerts).mockResolvedValue(MOCK_ALERTS);
    vi.mocked(deleteAlert).mockResolvedValue(undefined);

    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rule-1")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByLabelText("NVDA 알림 삭제"));
    await waitFor(() => {
      expect(deleteAlert).toHaveBeenCalledWith(1);
    });
  });
});
