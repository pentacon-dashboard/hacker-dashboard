import "@testing-library/jest-dom";

// jsdom 에서 scrollIntoView 미구현 — 단위 테스트용 mock
window.HTMLElement.prototype.scrollIntoView = function () {};

// jsdom 에서 ResizeObserver 미구현 — Recharts ResponsiveContainer 단위 테스트용 mock
if (typeof window.ResizeObserver === "undefined") {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// jsdom 에서 matchMedia 미구현 — ThemeProvider 의 system 테마 감지용 mock
if (typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}
