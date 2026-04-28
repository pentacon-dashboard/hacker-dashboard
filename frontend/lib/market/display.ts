const DOMESTIC_STOCK_MARKETS = new Set(["naver_kr", "krx", "kiwoom"]);

const KR_STOCK_NAMES: Record<string, string> = {
  "005930": "삼성전자",
  "000660": "SK하이닉스",
  "035420": "NAVER",
  "035720": "카카오",
  "005380": "현대차",
  "051910": "LG화학",
  "006400": "삼성SDI",
  "207940": "삼성바이오로직스",
  "005490": "POSCO홀딩스",
  "028260": "삼성물산",
};

export function isDomesticStockMarket(market: string | null | undefined): boolean {
  return DOMESTIC_STOCK_MARKETS.has((market ?? "").toLowerCase());
}

export function normalizeDomesticStockCode(code: string): string {
  const normalized = code.trim().toUpperCase().replace(/\.(KS|KQ)$/u, "");
  const digits = normalized.replace(/\D/gu, "");

  if (digits.length >= 6) {
    return digits.slice(0, 6);
  }

  return normalized;
}

export function getDomesticStockName(code: string): string | null {
  return KR_STOCK_NAMES[normalizeDomesticStockCode(code)] ?? null;
}

export function formatSymbolDisplay(
  market: string,
  code: string,
  options: { includeCode?: boolean } = {},
): string {
  if (!isDomesticStockMarket(market)) {
    return code;
  }

  const normalizedCode = normalizeDomesticStockCode(code);
  const name = getDomesticStockName(normalizedCode);

  if (name == null) {
    return normalizedCode;
  }

  if (options.includeCode === false) {
    return name;
  }

  return `${name} (${normalizedCode})`;
}
