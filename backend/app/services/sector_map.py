"""Deterministic ticker to GICS sector mapping.

The map is intentionally small and fixture-like. Unknown stock tickers fall
back to ``Other`` so reports can stay honest instead of inventing sectors.
Crypto and cash-like instruments are kept outside GICS as explicit buckets.
"""

from __future__ import annotations

GICS_SECTORS: tuple[str, ...] = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)

_SECTOR_MAP: dict[str, str] = {
    # Korean equities
    "005930": "Information Technology",
    "000660": "Information Technology",
    "035420": "Communication Services",
    "035720": "Communication Services",
    "005380": "Consumer Discretionary",
    "000270": "Consumer Discretionary",
    "068270": "Health Care",
    "207940": "Health Care",
    "006400": "Industrials",
    "051910": "Materials",
    "028260": "Industrials",
    "055550": "Financials",
    # US equities
    "AAPL": "Information Technology",
    "MSFT": "Information Technology",
    "NVDA": "Information Technology",
    "AMD": "Information Technology",
    "GOOGL": "Communication Services",
    "GOOG": "Communication Services",
    "META": "Communication Services",
    "NFLX": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "JPM": "Financials",
    "BAC": "Financials",
    "V": "Financials",
    "MA": "Financials",
    "JNJ": "Health Care",
    "UNH": "Health Care",
    "PFE": "Health Care",
    "XOM": "Energy",
    "CVX": "Energy",
    "NEE": "Utilities",
    "PLD": "Real Estate",
    "CAT": "Industrials",
    "LIN": "Materials",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
    # Non-GICS buckets
    "KRW-BTC": "Digital Assets",
    "KRW-ETH": "Digital Assets",
    "KRW-SOL": "Digital Assets",
    "KRW-XRP": "Digital Assets",
    "BTCUSDT": "Digital Assets",
    "ETHUSDT": "Digital Assets",
    "CASH": "Cash",
    "KRW": "Cash",
    "USD": "Cash",
}


def get_sector(ticker: str) -> str:
    """Return a deterministic GICS sector or explicit non-GICS bucket."""
    normalized = ticker.upper().strip()
    return _SECTOR_MAP.get(normalized, _SECTOR_MAP.get(ticker.strip(), "Other"))


def get_sector_map() -> dict[str, str]:
    """Return a copy of the static sector mapping."""
    return dict(_SECTOR_MAP)
