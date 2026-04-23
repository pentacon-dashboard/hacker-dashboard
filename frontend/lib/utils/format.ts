/**
 * 금융 데이터 포맷 유틸리티.
 * 모든 함수는 순수 함수 — 부수 효과 없음.
 * Decimal 값은 BE 에서 string 으로 내려오므로 Number() 로 변환 후 처리.
 */

/** ₩1,234,567 형식 */
export function formatKRW(n: number | string): string {
  const value = Number(n);
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency: "KRW",
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * ₩18.76M 같은 영문 K/M/B 축약 표기 — KPI 스트립 카드 잘림 방지용.
 * 목업 레이블과 정렬되도록 K(1e3)/M(1e6)/B(1e9)/T(1e12) 단위를 쓴다.
 */
export function formatKRWCompact(n: number | string): string {
  const value = Number(n);
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}₩${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}₩${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}₩${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}₩${(abs / 1e3).toFixed(1)}K`;
  return formatKRW(value);
}

/** $1,234.56 형식 */
export function formatUSD(n: number | string): string {
  const value = Number(n);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

interface FormatPctOptions {
  /** true 이면 양수에 + 기호 추가 */
  signed?: boolean;
  /** 소수점 자리수 (기본 2) */
  decimals?: number;
}

/** +2.34% 또는 -1.23% 형식 */
export function formatPct(
  n: number | string,
  { signed = false, decimals = 2 }: FormatPctOptions = {},
): string {
  const value = Number(n);
  const formatted = Math.abs(value).toFixed(decimals) + "%";
  if (value < 0) return `-${formatted}`;
  if (signed && value > 0) return `+${formatted}`;
  return formatted;
}

/** -12,345 형식 (부호 있는 숫자, 천 단위 구분) */
export function formatSignedNumber(n: number | string): string {
  const value = Number(n);
  const abs = new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 0,
  }).format(Math.abs(value));
  if (value < 0) return `-${abs}`;
  if (value > 0) return `+${abs}`;
  return abs;
}

/**
 * 값의 부호에 따라 Tailwind 색상 클래스를 반환하는 헬퍼.
 * @returns 양수 → 초록, 음수 → 빨강, 0 → 기본(muted)
 */
export function signedColorClass(n: number | string): string {
  const value = Number(n);
  if (value > 0) return "text-green-600 dark:text-green-400";
  if (value < 0) return "text-red-600 dark:text-red-400";
  return "text-muted-foreground";
}
