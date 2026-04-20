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
