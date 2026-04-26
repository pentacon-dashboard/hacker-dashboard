"""Yahoo Finance 어댑터 (해외주식 / 환율).

API:
  - GET https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=3mo
  - GET https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter

_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_SEARCH_BASE = "https://query1.finance.yahoo.com/v1/finance/search"

_INTERVAL_MAP = {
    "1d": "1d",
    "1m": "1m",
}
_RANGE_MAP = {
    "1d": "3mo",
    "1m": "1d",
}


class YahooAdapter(MarketAdapter):
    market = "yahoo"

    async def fetch_quote(self, symbol: str) -> Quote:
        data = await self._get(
            f"{_CHART_BASE}/{symbol}",
            params={"interval": "1d", "range": "2d"},
        )
        result = _extract_chart(data)
        meta = result.get("meta", {})
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose", 0))
        prev = float(meta.get("chartPreviousClose") or meta.get("previousClose", price))
        change = price - prev
        change_pct = (change / prev * 100) if prev != 0 else 0.0
        currency = meta.get("currency", "USD")
        ts = _epoch_to_iso(int(meta.get("regularMarketTime", 0)))
        return Quote(
            symbol=symbol,
            market=self.market,
            price=price,
            change=change,
            change_pct=change_pct,
            volume=float(meta.get("regularMarketVolume", 0)) or None,
            currency=currency,
            timestamp=ts,
        )

    async def fetch_ohlc(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 100,
    ) -> list[OhlcBar]:
        yi = _INTERVAL_MAP.get(interval, "1d")
        yr = _RANGE_MAP.get(interval, "3mo")
        data = await self._get(
            f"{_CHART_BASE}/{symbol}",
            params={"interval": yi, "range": yr},
        )
        result = _extract_chart(data)
        timestamps: list[int] = result.get("timestamp") or []
        indicators = result.get("indicators", {})
        quote_list: list[dict[str, Any]] = indicators.get("quote", [{}])
        q = quote_list[0] if quote_list else {}

        opens = q.get("open") or []
        highs = q.get("high") or []
        lows = q.get("low") or []
        closes = q.get("close") or []
        volumes = q.get("volume") or []

        bars: list[OhlcBar] = []
        for i, ts_epoch in enumerate(timestamps[-limit:]):
            if i >= len(closes) or closes[i] is None:
                continue
            bars.append(
                OhlcBar(
                    ts=_epoch_to_iso(ts_epoch),
                    open=float(opens[i])
                    if i < len(opens) and opens[i] is not None
                    else float(closes[i]),
                    high=float(highs[i])
                    if i < len(highs) and highs[i] is not None
                    else float(closes[i]),
                    low=float(lows[i])
                    if i < len(lows) and lows[i] is not None
                    else float(closes[i]),
                    close=float(closes[i]),
                    volume=float(volumes[i])
                    if i < len(volumes) and volumes[i] is not None
                    else None,
                )
            )
        return bars

    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        data = await self._get(
            _SEARCH_BASE,
            params={"q": query, "quotesCount": 20, "newsCount": 0},
        )
        results: list[SymbolInfo] = []
        for item in data.get("quotes", []):
            sym = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname") or sym
            qtype = item.get("quoteType", "EQUITY")
            asset_class = _map_asset_class(qtype)
            results.append(
                SymbolInfo(
                    symbol=sym,
                    name=name,
                    asset_class=asset_class,
                    exchange=item.get("exchange"),
                    market=self.market,
                    currency=item.get("currency"),
                )
            )
        return results


def _extract_chart(data: Any) -> dict[str, Any]:
    try:
        return data["chart"]["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Yahoo: unexpected response shape — {exc}") from exc


def _epoch_to_iso(epoch: int) -> str:
    try:
        return datetime.fromtimestamp(epoch, tz=UTC).isoformat()
    except (ValueError, OSError):
        return datetime.now(UTC).isoformat()


def _map_asset_class(qtype: str) -> str:
    mapping = {
        "EQUITY": "stock",
        "CRYPTOCURRENCY": "crypto",
        "CURRENCY": "fx",
        "ETF": "stock",
        "INDEX": "macro",
    }
    return mapping.get(qtype.upper(), "stock")
