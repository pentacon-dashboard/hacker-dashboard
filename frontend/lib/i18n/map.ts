/**
 * Translation helpers for BE-originated Korean data.
 *
 * Usage:
 *   const { t } = useLocale();
 *   translateSectorName("반도체", t)   // → "Semiconductor" in EN, "반도체" in KO
 *   translateSymbolName("005930", "삼성전자", t) // → "Samsung Electronics" in EN
 */

/**
 * Maps BE Korean sector names (and English fallback names) to i18n dictionary keys.
 * Keys cover both portfolio heatmap tiles and market-analyze sector grid.
 */
const SECTOR_NAME_TO_KEY: Record<string, string> = {
  // Korean names (BE primary)
  "정보기술": "portfolio.sector.technology",
  "반도체": "portfolio.sector.semiconductor",
  "금융": "portfolio.sector.financials",
  "헬스케어": "portfolio.sector.healthcare",
  "에너지": "portfolio.sector.energy",
  "소비재": "portfolio.sector.consumer",
  "산업재": "portfolio.sector.industrials",
  "소재": "portfolio.sector.materials",
  "유틸리티": "portfolio.sector.utilities",
  "부동산": "portfolio.sector.realEstate",
  "통신": "portfolio.sector.communication",
  "암호화폐": "portfolio.sector.crypto",
  "기술": "portfolio.sector.tech",
  // English names (BE may also send these)
  "Technology": "portfolio.sector.technology",
  "Semiconductor": "portfolio.sector.semiconductor",
  "Financials": "portfolio.sector.financials",
  "Healthcare": "portfolio.sector.healthcare",
  "Energy": "portfolio.sector.energy",
  "Consumer Disc.": "portfolio.sector.consumer",
  "Consumer Discretionary": "portfolio.sector.consumer",
  "Industrials": "portfolio.sector.industrials",
  "Materials": "portfolio.sector.materials",
  "Utilities": "portfolio.sector.utilities",
  "Real Estate": "portfolio.sector.realEstate",
  "Communication": "portfolio.sector.communication",
  "Communication Services": "portfolio.sector.communication",
  "Crypto": "portfolio.sector.crypto",
  "Tech": "portfolio.sector.tech",
  // market-analyze aliases (same keys, different Korean spelling)
  "IT / Technology": "portfolio.sector.technology",
  "IT": "portfolio.sector.technology",
};

type TFn = (key: string) => string;

/**
 * Translate a BE sector name string (Korean or English) to the current locale.
 * Falls back to the original `name` if no mapping is found.
 */
export function translateSectorName(name: string, t: TFn): string {
  const key = SECTOR_NAME_TO_KEY[name];
  if (!key) return name;
  const translated = t(key);
  // If translation key not found, t() returns the key itself — fall back to original
  return translated === key ? name : translated;
}

/**
 * Translate a BE symbol name using the stock code.
 * Falls back to `fallback` (usually the Korean name from BE) if no mapping is found.
 */
export function translateSymbolName(code: string, fallback: string, t: TFn): string {
  const key = `symbol.name.${code}`;
  const translated = t(key);
  // If translation key not found, t() returns the key itself — use fallback
  return translated === key ? fallback : translated;
}
