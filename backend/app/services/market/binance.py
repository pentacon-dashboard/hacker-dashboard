"""Binance 시장 데이터 어댑터.

API 문서: https://binance-docs.github.io/apidocs/spot/en/
엔드포인트:
  - GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT
  - GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=100
  - GET https://api.binance.com/api/v3/exchangeInfo  (심볼 목록)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter

_BASE = "https://api.binance.com/api/v3"

_INTERVAL_MAP = {
    "1d": "1d",
    "1m": "1m",
}


class BinanceAdapter(MarketAdapter):
    market = "binance"

    async def fetch_quote(self, symbol: str) -> Quote:
        data: dict[str, Any] = await self._get(
            f"{_BASE}/ticker/24hr",
            params={"symbol": symbol},
        )
        price = float(data["lastPrice"])
        change = float(data.get("priceChange", 0))
        change_pct = float(data.get("priceChangePercent", 0))
        volume = float(data.get("volume", 0)) or None
        ts = _ms_to_iso(int(data.get("closeTime", 0)))
        # 통화 추정: USDT 페어면 USDT, BTC 페어면 BTC 등
        currency = _infer_currency(symbol)
        return Quote(
            symbol=symbol,
            market=self.market,
            price=price,
            change=change,
            change_pct=change_pct,
            volume=volume,
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
        bi = _INTERVAL_MAP.get(interval, "1d")
        data: list[list[Any]] = await self._get(
            f"{_BASE}/klines",
            params={"symbol": symbol, "interval": bi, "limit": min(limit, 1000)},
        )
        bars: list[OhlcBar] = []
        for row in data:
            # [open_time, open, high, low, close, volume, close_time, ...]
            bars.append(
                OhlcBar(
                    ts=_ms_to_iso(int(row[0])),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]) or None,
                )
            )
        return bars

    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        data: dict[str, Any] = await self._get(f"{_BASE}/exchangeInfo")
        q = query.upper()
        results: list[SymbolInfo] = []
        for s in data.get("symbols", []):
            base: str = s.get("baseAsset", "")
            quote_asset: str = s.get("quoteAsset", "")
            sym: str = s.get("symbol", "")
            if q in sym or q in base:
                results.append(
                    SymbolInfo(
                        symbol=sym,
                        name=f"{base}/{quote_asset}",
                        asset_class="crypto",
                        exchange="Binance",
                        market=self.market,
                        currency=quote_asset,
                    )
                )
                if len(results) >= 20:
                    break
        return results


def _ms_to_iso(ms: int) -> str:
    """밀리초 epoch → ISO-8601 UTC."""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return datetime.now(timezone.utc).isoformat()


def _infer_currency(symbol: str) -> str:
    for suffix in ("USDT", "BUSD", "USD", "BTC", "ETH", "BNB"):
        if symbol.endswith(suffix):
            return suffix
    return "USDT"
