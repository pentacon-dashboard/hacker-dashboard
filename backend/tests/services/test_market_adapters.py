"""
시장 데이터 어댑터 단위 테스트.

respx로 외부 HTTP 호출을 모킹 — 실 네트워크 없이 동작.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.market.base import set_http_client
from app.services.market.binance import BinanceAdapter
from app.services.market.cache import cache_get, cache_set, quote_key, set_redis
from app.services.market.registry import get_adapter
from app.services.market.upbit import UpbitAdapter
from app.services.market.yahoo import YahooAdapter


@pytest.fixture(autouse=True)
def inject_http_client(respx_mock):
    """respx가 intercept할 수 있도록 httpx.AsyncClient를 공유 클라이언트에 주입."""
    client = AsyncClient()
    set_http_client(client)
    yield
    set_http_client(None)


@pytest.fixture(autouse=True)
def disable_redis():
    """테스트에서 Redis를 비활성화 (passthrough)."""
    set_redis(None)
    yield
    set_redis(None)


# ─────────────────────────── Upbit ────────────────────────────────────

class TestUpbitAdapter:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_quote(self):
        respx.get("https://api.upbit.com/v1/ticker").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "market": "KRW-BTC",
                        "trade_price": 45000000.0,
                        "signed_change_price": 500000.0,
                        "signed_change_rate": 0.012,
                        "acc_trade_volume_24h": 1234.5,
                        "trade_date_kst": "20240101",
                        "trade_time_kst": "120000",
                    }
                ],
            )
        )
        adapter = UpbitAdapter()
        quote = await adapter.fetch_quote("KRW-BTC")

        assert quote.symbol == "KRW-BTC"
        assert quote.price == 45000000.0
        assert quote.change == 500000.0
        assert abs(quote.change_pct - 1.2) < 0.001
        assert quote.currency == "KRW"
        assert quote.market == "upbit"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_ohlc(self):
        respx.get("https://api.upbit.com/v1/candles/days").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "candle_date_time_utc": "2024-01-02T00:00:00",
                        "opening_price": 44000000.0,
                        "high_price": 46000000.0,
                        "low_price": 43000000.0,
                        "trade_price": 45000000.0,
                        "candle_acc_trade_volume": 500.0,
                    },
                    {
                        "candle_date_time_utc": "2024-01-01T00:00:00",
                        "opening_price": 43000000.0,
                        "high_price": 45000000.0,
                        "low_price": 42000000.0,
                        "trade_price": 44000000.0,
                        "candle_acc_trade_volume": 400.0,
                    },
                ],
            )
        )
        adapter = UpbitAdapter()
        bars = await adapter.fetch_ohlc("KRW-BTC", interval="1d", limit=10)

        assert len(bars) == 2
        # reversed 확인 — 오래된 순서대로
        assert bars[0].open == 43000000.0  # 2024-01-01
        assert bars[1].open == 44000000.0  # 2024-01-02

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_symbols(self):
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(
                200,
                json=[
                    {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
                    {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
                    {"market": "BTC-XRP", "korean_name": "리플", "english_name": "Ripple"},
                ],
            )
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("BTC")

        assert len(results) >= 2
        symbols = [r.symbol for r in results]
        assert "KRW-BTC" in symbols
        assert "BTC-XRP" in symbols


# ─────────────────────────── Yahoo ────────────────────────────────────

class TestYahooAdapter:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_quote(self):
        respx.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL").mock(
            return_value=Response(
                200,
                json={
                    "chart": {
                        "result": [
                            {
                                "meta": {
                                    "regularMarketPrice": 185.0,
                                    "chartPreviousClose": 180.0,
                                    "currency": "USD",
                                    "regularMarketTime": 1704067200,
                                    "regularMarketVolume": 50000000,
                                }
                            }
                        ],
                        "error": None,
                    }
                },
            )
        )
        adapter = YahooAdapter()
        quote = await adapter.fetch_quote("AAPL")

        assert quote.symbol == "AAPL"
        assert quote.price == 185.0
        assert abs(quote.change - 5.0) < 0.001
        assert quote.currency == "USD"
        assert quote.market == "yahoo"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_ohlc(self):
        respx.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL").mock(
            return_value=Response(
                200,
                json={
                    "chart": {
                        "result": [
                            {
                                "meta": {"currency": "USD"},
                                "timestamp": [1704067200, 1704153600],
                                "indicators": {
                                    "quote": [
                                        {
                                            "open": [180.0, 182.0],
                                            "high": [186.0, 188.0],
                                            "low": [179.0, 181.0],
                                            "close": [185.0, 187.0],
                                            "volume": [50000000, 45000000],
                                        }
                                    ]
                                },
                            }
                        ],
                        "error": None,
                    }
                },
            )
        )
        adapter = YahooAdapter()
        bars = await adapter.fetch_ohlc("AAPL", interval="1d", limit=100)

        assert len(bars) == 2
        assert bars[0].open == 180.0
        assert bars[0].close == 185.0
        assert bars[1].close == 187.0

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_symbols(self):
        respx.get("https://query1.finance.yahoo.com/v1/finance/search").mock(
            return_value=Response(
                200,
                json={
                    "quotes": [
                        {
                            "symbol": "AAPL",
                            "longname": "Apple Inc.",
                            "quoteType": "EQUITY",
                            "exchange": "NMS",
                            "currency": "USD",
                        },
                        {
                            "symbol": "AAPLX",
                            "shortname": "Apple Growth Fund",
                            "quoteType": "MUTUALFUND",
                            "exchange": "NAS",
                            "currency": "USD",
                        },
                    ]
                },
            )
        )
        adapter = YahooAdapter()
        results = await adapter.search_symbols("AAPL")

        assert len(results) == 2
        assert results[0].symbol == "AAPL"
        assert results[0].asset_class == "stock"


# ─────────────────────────── Binance ──────────────────────────────────

class TestBinanceAdapter:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_quote(self):
        respx.get("https://api.binance.com/api/v3/ticker/24hr").mock(
            return_value=Response(
                200,
                json={
                    "symbol": "BTCUSDT",
                    "lastPrice": "45000.00",
                    "priceChange": "500.00",
                    "priceChangePercent": "1.12",
                    "volume": "12345.678",
                    "closeTime": 1704153600000,
                },
            )
        )
        adapter = BinanceAdapter()
        quote = await adapter.fetch_quote("BTCUSDT")

        assert quote.symbol == "BTCUSDT"
        assert quote.price == 45000.0
        assert quote.change == 500.0
        assert abs(quote.change_pct - 1.12) < 0.001
        assert quote.currency == "USDT"
        assert quote.market == "binance"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_ohlc(self):
        respx.get("https://api.binance.com/api/v3/klines").mock(
            return_value=Response(
                200,
                json=[
                    [1704067200000, "44000", "46000", "43000", "45000", "1000", 1704153599999, "45000000", 5000, "500", "22500000", "0"],
                    [1704153600000, "45000", "47000", "44500", "46500", "900", 1704239999999, "41850000", 4500, "450", "20925000", "0"],
                ],
            )
        )
        adapter = BinanceAdapter()
        bars = await adapter.fetch_ohlc("BTCUSDT", interval="1d", limit=10)

        assert len(bars) == 2
        assert bars[0].open == 44000.0
        assert bars[0].close == 45000.0
        assert bars[1].close == 46500.0

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_symbols(self):
        respx.get("https://api.binance.com/api/v3/exchangeInfo").mock(
            return_value=Response(
                200,
                json={
                    "symbols": [
                        {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT"},
                        {"symbol": "BTCBUSD", "baseAsset": "BTC", "quoteAsset": "BUSD"},
                        {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT"},
                    ]
                },
            )
        )
        adapter = BinanceAdapter()
        results = await adapter.search_symbols("BTC")

        assert len(results) == 2
        symbols = [r.symbol for r in results]
        assert "BTCUSDT" in symbols
        assert "BTCBUSD" in symbols


# ─────────────────────────── 캐시 ─────────────────────────────────────

class TestCachePassthrough:
    @pytest.mark.asyncio
    async def test_cache_get_returns_none_when_no_redis(self):
        """Redis 미연결(None)이면 cache_get은 None 반환."""
        set_redis(None)
        result = await cache_get("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_noop_when_no_redis(self):
        """Redis 미연결이면 cache_set은 예외 없이 pass."""
        set_redis(None)
        await cache_set("test:key", {"price": 100}, ttl=5)  # 예외 없어야 함


class TestCacheHit:
    @pytest.mark.asyncio
    async def test_cache_hit_with_fake_redis(self):
        """캐시 히트 시 저장된 값이 반환된다."""
        import redis.asyncio as aioredis

        # fakeredis 대신 간단한 dict 기반 가짜 redis 구현
        class FakeRedis:
            def __init__(self):
                self._store = {}

            async def get(self, key):
                return self._store.get(key)

            async def set(self, key, value, ex=None):
                self._store[key] = value

        fake = FakeRedis()
        set_redis(fake)  # type: ignore[arg-type]

        try:
            await cache_set("test:hit", {"price": 42.0}, ttl=5)
            result = await cache_get("test:hit")
            assert result is not None
            assert result["price"] == 42.0
        finally:
            set_redis(None)
