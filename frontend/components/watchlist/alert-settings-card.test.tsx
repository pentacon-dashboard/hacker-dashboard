import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LocaleProvider } from "@/lib/i18n/locale-provider";
import { AlertSettingsCard } from "./alert-settings-card";
import type { WatchlistAlert, WatchlistItemResponse } from "@/lib/api/watchlist";

vi.mock("@/lib/api/watchlist", () => ({
  getAlerts: vi.fn(),
  createAlert: vi.fn(),
  updateAlert: vi.fn(),
  deleteAlert: vi.fn(),
  listWatchlist: vi.fn(),
}));

import {
  getAlerts,
  createAlert,
  updateAlert,
  deleteAlert,
  listWatchlist,
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

const MOCK_WATCHLIST: WatchlistItemResponse[] = [
  {
    id: 1,
    market: "yahoo",
    code: "AAPL",
    created_at: "2026-04-20T00:00:00Z",
  },
];

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <LocaleProvider>{children}</LocaleProvider>
      </QueryClientProvider>
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listWatchlist).mockResolvedValue(MOCK_WATCHLIST);
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
    expect(screen.getByText("NVIDIA")).toBeInTheDocument();
    expect(screen.getByText("비트코인")).toBeInTheDocument();
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

    fireEvent.click(screen.getByLabelText("+ 추가"));
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

    fireEvent.click(screen.getByLabelText("+ 추가"));
    await waitFor(() =>
      expect(screen.getByTestId("add-alert-form")).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText("티커 (예: AAPL)"), {
      target: { value: "yahoo|AAPL" },
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

    fireEvent.click(screen.getByLabelText("NVIDIA 끄기"));
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

    fireEvent.click(screen.getByLabelText("NVIDIA 알림 삭제"));
    await waitFor(() => {
      expect(deleteAlert).toHaveBeenCalledWith(1);
    });
  });

  it("손상된 심볼은 복구용 라벨로 표시하고 토글을 숨긴다", async () => {
    vi.mocked(getAlerts).mockResolvedValue([
      {
        id: 9,
        user_id: "demo",
        symbol: "􎦷󱳲µh",
        market: "upbit",
        direction: "above",
        threshold: "4.2300",
        enabled: true,
        created_at: "2026-04-20T00:00:00Z",
      },
    ]);

    render(<AlertSettingsCard />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("alert-rules-list")).toBeInTheDocument(),
    );

    expect(screen.getByText("손상된 알림 #9")).toBeInTheDocument();
    expect(screen.queryByLabelText("손상된 알림 #9 끄기")).not.toBeInTheDocument();
    expect(screen.getByLabelText("손상된 알림 #9 알림 삭제")).toBeInTheDocument();
  });
});
