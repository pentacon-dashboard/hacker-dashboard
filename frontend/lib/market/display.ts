const DOMESTIC_STOCK_MARKETS = new Set(["naver_kr", "krx", "kiwoom"]);

const KNOWN_SYMBOL_NAMES: Record<string, string> = {
  "AAPL": "Apple",
  "AMZN": "Amazon",
  "GOOGL": "Alphabet",
  "KRW-BTC": "비트코인",
  "KRW-ETH": "이더리움",
  "META": "Meta",
  "MSFT": "Microsoft",
  "NVDA": "NVIDIA",
  "TSLA": "Tesla",
};

const GENERIC_SYMBOL_RE = /^[A-Z0-9][A-Z0-9._:/-]{0,31}$/u;

const KR_STOCK_NAMES: Record<string, string> = {
  "000660": "SK Hynix",
  "005380": "현대차",
  "005490": "POSCO홀딩스",
  "005930": "삼성전자",
  "006400": "삼성SDI",
  "028260": "삼성물산",
  "035420": "NAVER",
  "035720": "카카오",
  "051910": "LG화학",
  "207940": "삼성바이오로직스",
};

export interface SymbolDisplayParts {
  primary: string;
  secondary: string | null;
  normalizedCode: string;
}

export function isDomesticStockMarket(market: string | null | undefined): boolean {
  return DOMESTIC_STOCK_MARKETS.has((market ?? "").toLowerCase());
}

function looksLikeDomesticStockCode(code: string): boolean {
  return /^\d{6}(?:\.(KS|KQ))?$/u.test(code.trim().toUpperCase());
}

function shouldUseDomesticStockRules(
  market: string | null | undefined,
  code: string,
): boolean {
  return isDomesticStockMarket(market) || looksLikeDomesticStockCode(code);
}

export function normalizeDomesticStockCode(code: string): string {
  const normalized = code.trim().toUpperCase().replace(/\.(KS|KQ)$/u, "");
  const digits = normalized.replace(/\D/gu, "");

  if (digits.length >= 6) {
    return digits.slice(0, 6);
  }

  return normalized;
}

export function normalizeSymbolCode(
  market: string | null | undefined,
  code: string,
): string {
  if (shouldUseDomesticStockRules(market, code)) {
    return normalizeDomesticStockCode(code);
  }

  return code.trim().toUpperCase();
}

export function isValidSymbolCode(
  market: string | null | undefined,
  code: string | null | undefined,
): boolean {
  const normalizedCode = normalizeSymbolCode(market, code ?? "");
  if (!GENERIC_SYMBOL_RE.test(normalizedCode)) {
    return false;
  }

  switch ((market ?? "").trim().toLowerCase()) {
    case "upbit":
      return /^[A-Z]{2,5}-[A-Z0-9]{2,12}$/u.test(normalizedCode);
    case "binance":
      return /^[A-Z0-9]{5,20}$/u.test(normalizedCode);
    case "yahoo":
    case "nasdaq":
    case "nyse":
      return /^[A-Z][A-Z0-9.-]{0,15}$/u.test(normalizedCode);
    case "naver_kr":
    case "krx":
    case "kiwoom":
      return /^\d{6}$/u.test(normalizedCode);
    default:
      return false;
  }
}

export function getDomesticStockName(code: string): string | null {
  return KR_STOCK_NAMES[normalizeDomesticStockCode(code)] ?? null;
}

export function getKnownSymbolName(
  market: string | null | undefined,
  code: string,
): string | null {
  if (shouldUseDomesticStockRules(market, code)) {
    return getDomesticStockName(code);
  }

  return KNOWN_SYMBOL_NAMES[normalizeSymbolCode(market, code)] ?? null;
}

export function resolveSymbolName(
  market: string | null | undefined,
  code: string,
  fallbackName?: string | null,
): string {
  const knownName = getKnownSymbolName(market, code);
  if (knownName != null) {
    return knownName;
  }

  const trimmedFallback = fallbackName?.trim();
  if (trimmedFallback) {
    return trimmedFallback;
  }

  return normalizeSymbolCode(market, code);
}

export function getSymbolDisplayParts(
  market: string | null | undefined,
  code: string,
  options: {
    fallbackName?: string | null;
    includeMarket?: boolean;
  } = {},
): SymbolDisplayParts {
  const normalizedCode = normalizeSymbolCode(market, code);
  const primary = resolveSymbolName(market, code, options.fallbackName);
  const secondaryParts: string[] = [];

  if (primary !== normalizedCode) {
    secondaryParts.push(normalizedCode);
  }

  if (options.includeMarket !== false && market) {
    secondaryParts.push(market);
  }

  return {
    primary,
    secondary: secondaryParts.length > 0 ? secondaryParts.join(" · ") : null,
    normalizedCode,
  };
}

export function formatSymbolDisplay(
  market: string,
  code: string,
  options: { includeCode?: boolean; fallbackName?: string | null } = {},
): string {
  const normalizedCode = normalizeSymbolCode(market, code);
  const name = resolveSymbolName(market, code, options.fallbackName);

  if (name === normalizedCode) {
    return normalizedCode;
  }

  if (options.includeCode === false) {
    return name;
  }

  return `${name} (${normalizedCode})`;
}
