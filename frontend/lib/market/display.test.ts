import { describe, it, expect } from "vitest";
import {
  formatSymbolDisplay,
  getSymbolDisplayParts,
  normalizeSymbolCode,
} from "./display";

describe("market display helpers", () => {
  it("normalizes domestic yahoo symbols to six-digit codes", () => {
    expect(normalizeSymbolCode("naver_kr", "005930.KS")).toBe("005930");
  });

  it("formats Korean stock names with codes", () => {
    expect(formatSymbolDisplay("naver_kr", "005930.KS")).toBe("삼성전자 (005930)");
  });

  it("formats known US and crypto symbols with friendly names", () => {
    expect(formatSymbolDisplay("yahoo", "NVDA", { includeCode: false })).toBe("NVIDIA");
    expect(formatSymbolDisplay("upbit", "KRW-BTC", { includeCode: false })).toBe("비트코인");
  });

  it("builds secondary label metadata when a name is available", () => {
    expect(getSymbolDisplayParts("yahoo", "NVDA")).toEqual({
      primary: "NVIDIA",
      secondary: "NVDA · yahoo",
      normalizedCode: "NVDA",
    });
  });
});
