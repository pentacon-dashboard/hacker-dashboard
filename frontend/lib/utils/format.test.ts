import { describe, it, expect } from "vitest";
import {
  formatKRW,
  formatUSD,
  formatPct,
  formatSignedNumber,
  signedColorClass,
} from "./format";

describe("formatKRW", () => {
  it("양수를 ₩ 형식으로 변환한다", () => {
    expect(formatKRW(1234567)).toBe("₩1,234,567");
  });

  it("0을 올바르게 처리한다", () => {
    expect(formatKRW(0)).toBe("₩0");
  });

  it("string 입력을 처리한다", () => {
    expect(formatKRW("9000000")).toBe("₩9,000,000");
  });

  it("음수도 처리한다", () => {
    expect(formatKRW(-500)).toBe("-₩500");
  });
});

describe("formatUSD", () => {
  it("양수를 $ 형식으로 변환한다", () => {
    expect(formatUSD(1234.56)).toBe("$1,234.56");
  });

  it("소수점 2자리를 유지한다", () => {
    expect(formatUSD(1.1)).toBe("$1.10");
  });

  it("string 입력을 처리한다", () => {
    expect(formatUSD("500.5")).toBe("$500.50");
  });

  it("0을 올바르게 처리한다", () => {
    expect(formatUSD(0)).toBe("$0.00");
  });
});

describe("formatPct", () => {
  it("기본 포맷 (signed 없음)", () => {
    expect(formatPct(2.34)).toBe("2.34%");
  });

  it("양수에 + 부호 추가 (signed: true)", () => {
    expect(formatPct(2.34, { signed: true })).toBe("+2.34%");
  });

  it("음수에 - 부호 추가", () => {
    expect(formatPct(-1.23, { signed: true })).toBe("-1.23%");
  });

  it("0은 부호 없이", () => {
    expect(formatPct(0, { signed: true })).toBe("0.00%");
  });

  it("string 입력 처리", () => {
    expect(formatPct("5.678", { decimals: 1 })).toBe("5.7%");
  });

  it("decimals 옵션 적용", () => {
    expect(formatPct(3.14159, { decimals: 3 })).toBe("3.142%");
  });
});

describe("formatSignedNumber", () => {
  it("양수에 + 부호와 천 단위 구분자", () => {
    expect(formatSignedNumber(12345)).toBe("+12,345");
  });

  it("음수에 - 부호와 천 단위 구분자", () => {
    expect(formatSignedNumber(-12345)).toBe("-12,345");
  });

  it("0은 부호 없이", () => {
    expect(formatSignedNumber(0)).toBe("0");
  });

  it("string 입력 처리", () => {
    expect(formatSignedNumber("-500000")).toBe("-500,000");
  });
});

describe("signedColorClass", () => {
  it("양수이면 초록색 클래스 반환", () => {
    expect(signedColorClass(100)).toContain("green");
  });

  it("음수이면 빨간색 클래스 반환", () => {
    expect(signedColorClass(-1)).toContain("red");
  });

  it("0이면 muted 클래스 반환", () => {
    expect(signedColorClass(0)).toContain("muted");
  });

  it("string 입력 처리", () => {
    expect(signedColorClass("0.05")).toContain("green");
  });
});
