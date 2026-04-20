"""
Symbol 검색 / Quote / OHLC API 테스트.

respx로 외부 호출을 모킹.
"""
from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.market.base import set_http_client
from app.services.market.cache import set_redis


@pytest.fixture(autouse=True)
def inject_http_client(respx_mock):
    from httpx import AsyncClient as HxClient
    client = HxClient()
    set_http_client(client)
    yield
    set_http_client(None)


@pytest.fixture(autouse=True)
def disable_redis():
    set_redis(None)
    yield
    set_redis(None)


# ─────────────────────────── 심볼 검색 ─────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_search_symbols_returns_list(client: AsyncClient) -> None:
    # Upbit mock
    respx.get("https://api.upbit.com/v1/market/all").mock(
        return_value=Response(
            200,
            json=[
                {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
            ],
        )
    )
    # Yahoo mock
    respx.get("https://query1.finance.yahoo.com/v1/finance/search").mock(
        return_value=Response(200, json={"quotes": []})
    )

    resp = await client.get("/market/symbols/search?q=BTC")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["symbol"] == "KRW-BTC" for item in data)


@respx.mock
@pytest.mark.asyncio
async def test_search_symbols_empty_result(client: AsyncClient) -> None:
    respx.get("https://api.upbit.com/v1/market/all").mock(
        return_value=Response(200, json=[])
    )
    respx.get("https://query1.finance.yahoo.com/v1/finance/search").mock(
        return_value=Response(200, json={"quotes": []})
    )

    resp = await client.get("/market/symbols/search?q=XYZNOTFOUND")
    assert resp.status_code == 200
    assert resp.json() == []


# ─────────────────────────── Quote 조회 ────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_get_quote_upbit(client: AsyncClient) -> None:
    respx.get("https://api.upbit.com/v1/ticker").mock(
        return_value=Response(
            200,
            json=[
                {
                    "market": "KRW-BTC",
                    "trade_price": 50000000.0,
                    "signed_change_price": 0.0,
                    "signed_change_rate": 0.0,
                    "acc_trade_volume_24h": 100.0,
                    "trade_date_kst": "20240101",
                    "trade_time_kst": "090000",
                }
            ],
        )
    )
    resp = await client.get("/market/quotes/upbit/KRW-BTC")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "KRW-BTC"
    assert data["price"] == 50000000.0
    assert data["market"] == "upbit"


@respx.mock
@pytest.mark.asyncio
async def test_get_quote_yahoo(client: AsyncClient) -> None:
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL").mock(
        return_value=Response(
            200,
            json={
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": 190.0,
                                "chartPreviousClose": 185.0,
                                "currency": "USD",
                                "regularMarketTime": 1704153600,
                                "regularMarketVolume": 40000000,
                            }
                        }
                    ],
                    "error": None,
                }
            },
        )
    )
    resp = await client.get("/market/quotes/yahoo/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 190.0
    assert data["currency"] == "USD"


@pytest.mark.asyncio
async def test_get_quote_unknown_market(client: AsyncClient) -> None:
    resp = await client.get("/market/quotes/unknown_market/AAPL")
    assert resp.status_code == 404


# ─────────────────────────── OHLC 조회 ─────────────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_get_ohlc_binance(client: AsyncClient) -> None:
    respx.get("https://api.binance.com/api/v3/klines").mock(
        return_value=Response(
            200,
            json=[
                [1704067200000, "44000", "46000", "43000", "45000", "1000",
                 1704153599999, "45000000", 5000, "500", "22500000", "0"],
            ],
        )
    )
    resp = await client.get("/market/ohlc/binance/BTCUSDT?interval=1d&limit=10")
    assert resp.status_code == 200
    bars = resp.json()
    assert len(bars) == 1
    assert bars[0]["open"] == 44000.0
    assert bars[0]["close"] == 45000.0


@respx.mock
@pytest.mark.asyncio
async def test_get_ohlc_returns_empty_for_naver_stub(client: AsyncClient) -> None:
    resp = await client.get("/market/ohlc/naver_kr/005930?interval=1d&limit=10")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_ohlc_invalid_interval(client: AsyncClient) -> None:
    resp = await client.get("/market/ohlc/upbit/KRW-BTC?interval=invalid")
    assert resp.status_code == 422
