import type { Citation } from "@/lib/api/news";
import type { HoldingDetail } from "@/lib/api/portfolio";

const HTTP_URL_PATTERN = /^https?:\/\//iu;
const CONTROL_CHAR_PATTERN = /[\u0000-\u001f\u007f]/u;
const GENERIC_CODE_PATTERN = /^[A-Z0-9][A-Z0-9._:/-]{0,31}$/u;
const CURRENCY_PATTERN = /^[A-Z]{3,5}$/u;

function normalizeToken(value: string | null | undefined): string {
  return (value ?? "").trim().toUpperCase();
}

function hasControlChars(value: string | null | undefined): boolean {
  return CONTROL_CHAR_PATTERN.test(value ?? "");
}

function isDisplayableSymbol(market: string, code: string): boolean {
  if (!GENERIC_CODE_PATTERN.test(code)) {
    return false;
  }

  switch (market.toLowerCase()) {
    case "upbit":
      return /^[A-Z]{2,5}-[A-Z0-9]{2,12}$/u.test(code);
    case "binance":
      return /^[A-Z0-9]{5,20}$/u.test(code);
    case "yahoo":
    case "nasdaq":
    case "nyse":
      return /^[A-Z][A-Z0-9.-]{0,15}$/u.test(code);
    case "naver_kr":
    case "krx":
    case "kiwoom":
      return /^\d{6}(\.(KS|KQ))?$/u.test(code);
    default:
      return true;
  }
}

export function isDisplayableHolding(holding: HoldingDetail): boolean {
  const market = (holding.market ?? "").trim();
  const code = normalizeToken(holding.code);
  const currency = normalizeToken(holding.currency);

  if (market.length === 0 || code.length === 0 || currency.length === 0) {
    return false;
  }

  if (hasControlChars(holding.code) || hasControlChars(holding.currency)) {
    return false;
  }

  return isDisplayableSymbol(market, code) && CURRENCY_PATTERN.test(currency);
}

export function getDisplayableHoldings(holdings: HoldingDetail[]): HoldingDetail[] {
  return holdings.filter(isDisplayableHolding);
}

export function getDisplayableHoldingSymbols(holdings: HoldingDetail[]): string[] {
  return Array.from(
    new Set(
      getDisplayableHoldings(holdings).map((holding) => normalizeToken(holding.code)),
    ),
  );
}

export function buildDashboardNewsQuery(holdings: HoldingDetail[]): string | undefined {
  const symbols = getDisplayableHoldingSymbols(holdings).slice(0, 5);
  return symbols.length > 0 ? symbols.join(" OR ") : undefined;
}

export function isDisplayableCitation(citation: Citation): boolean {
  const title = citation.title.trim();
  const sourceUrl = citation.source_url.trim();

  if (title.length === 0 || sourceUrl.length === 0) {
    return false;
  }

  if (hasControlChars(title) || hasControlChars(sourceUrl)) {
    return false;
  }

  if (!HTTP_URL_PATTERN.test(sourceUrl)) {
    return false;
  }

  try {
    const url = new URL(sourceUrl);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function sanitizeCitations(citations: Citation[]): Citation[] {
  return citations.filter(isDisplayableCitation);
}
