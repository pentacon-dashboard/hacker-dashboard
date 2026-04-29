"""Kiwoom REST market data adapter.

Scope for this integration is intentionally narrow: use Kiwoom for KRX quote
lookups and keep the existing Naver/yfinance adapter as a safe fallback for
search and chart data. Secrets stay in environment variables only.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter, get_http_client

logger = logging.getLogger(__name__)

_TOKEN_PATH = "/oauth2/token"
_STOCK_INFO_PATH = "/api/dostk/stkinfo"
_STOCK_INFO_API_ID = "ka10001"
_TOKEN_REFRESH_SKEW = timedelta(minutes=5)


class KiwoomAdapter(MarketAdapter):
    """Kiwoom REST adapter for domestic stock quote reads.

    The adapter can be mounted under multiple domestic market aliases
    (``kiwoom``, ``krx``, ``naver_kr``). When credentials are absent or Kiwoom
    is temporarily unavailable, it delegates to the configured fallback adapter.
    """

    def __init__(self, *, market: str = "kiwoom", fallback: MarketAdapter | None = None) -> None:
        self.market = market
        self._fallback = fallback
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    async def fetch_quote(self, symbol: str) -> Quote:
        code = _normalize_krx_code(symbol)
        if not code:
            return await self._fallback_quote(symbol, "invalid domestic symbol")

        if not _has_credentials():
            return await self._fallback_quote(code, "kiwoom credentials not configured")

        try:
            data = await self._post_kiwoom(_STOCK_INFO_PATH, _STOCK_INFO_API_ID, {"stk_cd": code})
            quote = _quote_from_stock_info(data, code, self.market)
            if quote is None:
                return await self._fallback_quote(code, "kiwoom quote response missing price")
            return quote
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kiwoom quote failed for %s: %s", code, exc)
            return await self._fallback_quote(code, "kiwoom quote failed")

    async def fetch_ohlc(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 100,
    ) -> list[OhlcBar]:
        # Keep chart behavior stable for the first Kiwoom rollout. Quote data is
        # the piece that feeds portfolio valuation; OHLC can continue through the
        # existing domestic fallback until chart TR parsing is implemented.
        if self._fallback is not None:
            return await self._fallback.fetch_ohlc(
                _normalize_krx_code(symbol) or symbol, interval=interval, limit=limit
            )
        raise ValueError("Kiwoom OHLC fallback is not configured")

    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        if self._fallback is None:
            return []

        results = await self._fallback.search_symbols(query)
        normalized: list[SymbolInfo] = []
        for item in results:
            code = _normalize_krx_code(item.symbol)
            if code and (item.currency or "").upper() == "KRW":
                normalized.append(
                    item.model_copy(
                        update={
                            "symbol": code,
                            "market": self.market,
                            "exchange": item.exchange or "KRX",
                            "currency": "KRW",
                        }
                    )
                )
            else:
                normalized.append(item)
        return normalized

    async def _post_kiwoom(self, path: str, api_id: str, body: dict[str, Any]) -> dict[str, Any]:
        token = await self._get_access_token()
        client = get_http_client()
        resp = await client.post(
            f"{_base_url()}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "api-id": api_id,
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Kiwoom response is not a JSON object")
        return data

    async def _get_access_token(self) -> str:
        now = datetime.now(UTC)
        if (
            self._token
            and self._token_expires_at
            and now < self._token_expires_at - _TOKEN_REFRESH_SKEW
        ):
            return self._token

        async with self._token_lock:
            now = datetime.now(UTC)
            if (
                self._token
                and self._token_expires_at
                and now < self._token_expires_at - _TOKEN_REFRESH_SKEW
            ):
                return self._token

            client = get_http_client()
            resp = await client.post(
                f"{_base_url()}{_TOKEN_PATH}",
                headers={
                    "Content-Type": "application/json;charset=UTF-8",
                    "Accept": "application/json",
                },
                json={
                    "grant_type": "client_credentials",
                    "appkey": settings.kiwoom_app_key,
                    "secretkey": settings.kiwoom_secret_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("token") or data.get("access_token")
            if not isinstance(token, str) or not token.strip():
                raise ValueError("Kiwoom token response missing token")

            self._token = token.strip()
            self._token_expires_at = _parse_expires_at(data.get("expires_dt"))
            return self._token

    async def _fallback_quote(self, symbol: str, reason: str) -> Quote:
        if self._fallback is None:
            raise ValueError(reason)
        logger.info("Kiwoom fallback quote for %s: %s", symbol, reason)
        quote = await self._fallback.fetch_quote(_normalize_krx_code(symbol) or symbol)
        return quote.model_copy(update={"market": self.market})


def _has_credentials() -> bool:
    return bool(settings.kiwoom_app_key.strip() and settings.kiwoom_secret_key.strip())


def _base_url() -> str:
    return settings.kiwoom_base_url.rstrip("/") or "https://api.kiwoom.com"


def _normalize_krx_code(symbol: str) -> str:
    raw = symbol.strip().upper()
    raw = re.sub(r"\.(KS|KQ)$", "", raw)
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 6:
        return digits[:6]
    return ""


def _parse_expires_at(value: Any) -> datetime:
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text[:19], fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime.now(UTC) + timedelta(minutes=50)


def _quote_from_stock_info(data: dict[str, Any], code: str, market: str) -> Quote | None:
    price = _abs_float(_pick(data, "cur_prc", "curr_prc", "now_prc", "stck_prpr", "price"))
    if price is None or price <= 0:
        return None

    change = _to_float(_pick(data, "pred_pre", "prdy_vrss", "change", "diff")) or 0.0
    change_pct = _to_float(_pick(data, "flu_rt", "prdy_ctrt", "change_pct", "rate")) or 0.0
    volume = _abs_float(_pick(data, "trde_qty", "acml_vol", "volume"))
    timestamp = datetime.now(UTC).isoformat()

    return Quote(
        symbol=code,
        market=market,
        price=price,
        change=change,
        change_pct=change_pct,
        volume=volume,
        currency="KRW",
        timestamp=timestamp,
    )


def _pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _abs_float(value: Any) -> float | None:
    parsed = _to_float(value)
    return abs(parsed) if parsed is not None else None


def _to_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "")
    text = text.replace("▲", "+").replace("△", "+").replace("▼", "-").replace("▽", "-")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None
