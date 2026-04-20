import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRealtimeTicker } from "./use-realtime-ticker";
import { useTickersStore } from "@/stores/tickers";

// WebSocket mock
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    // 비동기로 onopen 호출
    setTimeout(() => this.onopen?.(new Event("open")), 0);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close"));
  }

  send(_data: string) {}

  // 테스트 helper
  static instances: MockWebSocket[] = [];
  static reset() {
    MockWebSocket.instances = [];
  }

  triggerMessage(data: object) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(data) }),
    );
  }
}

// global WebSocket 교체
vi.stubGlobal("WebSocket", MockWebSocket);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useRealtimeTicker", () => {
  beforeEach(() => {
    MockWebSocket.reset();
    // store 초기화
    useTickersStore.setState({ tickers: {} });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("올바른 URL 로 WebSocket 을 연결한다", async () => {
    const { unmount } = renderHook(
      () =>
        useRealtimeTicker([{ market: "upbit", code: "KRW-BTC" }]),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0]?.url).toContain("upbit%3AKRW-BTC");
    unmount();
  });

  it("WS 메시지 수신 시 Zustand store 에 ticker 를 upsert 한다", async () => {
    const { unmount } = renderHook(
      () =>
        useRealtimeTicker([{ market: "upbit", code: "KRW-BTC" }]),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      ws?.triggerMessage({
        market: "upbit",
        symbol: "KRW-BTC",
        price: 90_000_000,
        change_pct: 2.5,
        volume: 1234,
        ts: "2026-04-19T10:00:00Z",
      });
    });

    const { tickers } = useTickersStore.getState();
    expect(tickers["upbit:KRW-BTC"]).toBeDefined();
    expect(tickers["upbit:KRW-BTC"]?.price).toBe(90_000_000);
    expect(tickers["upbit:KRW-BTC"]?.change_pct).toBe(2.5);

    unmount();
  });

  it("잘못된 형식의 메시지는 무시한다", async () => {
    const { unmount } = renderHook(
      () =>
        useRealtimeTicker([{ market: "binance", code: "BTCUSDT" }]),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    const ws = MockWebSocket.instances[0];

    act(() => {
      ws?.onmessage?.(
        new MessageEvent("message", { data: "not-json{{{" }),
      );
    });

    const { tickers } = useTickersStore.getState();
    expect(Object.keys(tickers)).toHaveLength(0);

    unmount();
  });

  it("symbols 가 비어 있으면 WebSocket 을 연결하지 않는다", () => {
    const { unmount } = renderHook(() => useRealtimeTicker([]), {
      wrapper: makeWrapper(),
    });
    expect(MockWebSocket.instances).toHaveLength(0);
    unmount();
  });

  it("unmount 시 WebSocket 을 닫는다", async () => {
    const { unmount } = renderHook(
      () =>
        useRealtimeTicker([{ market: "upbit", code: "KRW-BTC" }]),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    unmount();

    expect(ws?.readyState).toBe(MockWebSocket.CLOSED);
  });
});
