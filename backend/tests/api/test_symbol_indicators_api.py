"""
Symbol Indicators API 통합 테스트 — Sprint-08 B-3.

GET /market/symbol/{market}/{code}/indicators
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_VALID_INTERVALS = ["1m", "5m", "15m", "60m", "day", "week", "month"]


@pytest.mark.asyncio
async def test_indicators_default(client: AsyncClient) -> None:
    resp = await client.get("/market/symbol/yahoo/AAPL/indicators")
    assert resp.status_code == 200
    data = resp.json()
    assert "interval" in data
    assert "period" in data
    assert data["interval"] == "day"
    assert data["period"] == 60


@pytest.mark.asyncio
async def test_indicators_schema(client: AsyncClient) -> None:
    """응답 스키마 전체 필드 확인."""
    resp = await client.get("/market/symbol/upbit/KRW-BTC/indicators")
    assert resp.status_code == 200
    data = resp.json()

    required_fields = [
        "interval",
        "period",
        "rsi_14",
        "macd",
        "bollinger",
        "stochastic",
        "metrics",
        "signal",
    ]
    for field in required_fields:
        assert field in data, f"필드 누락: {field}"

    assert "upper" in data["bollinger"]
    assert "mid" in data["bollinger"]
    assert "lower" in data["bollinger"]

    metrics = data["metrics"]
    assert "rsi_latest" in metrics
    assert "macd_latest" in metrics
    assert "macd_signal" in metrics
    assert "bollinger_position" in metrics

    assert data["signal"] in ("buy", "hold", "sell")


@pytest.mark.asyncio
@pytest.mark.parametrize("interval", _VALID_INTERVALS)
async def test_indicators_all_intervals(client: AsyncClient, interval: str) -> None:
    """7가지 interval 모두 200 응답."""
    resp = await client.get(f"/market/symbol/yahoo/AAPL/indicators?interval={interval}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval"] == interval


@pytest.mark.asyncio
async def test_indicators_invalid_interval(client: AsyncClient) -> None:
    resp = await client.get("/market/symbol/yahoo/AAPL/indicators?interval=invalid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_indicators_rsi_range(client: AsyncClient) -> None:
    """RSI 는 항상 0~100 범위."""
    resp = await client.get("/market/symbol/yahoo/AAPL/indicators")
    data = resp.json()
    for point in data["rsi_14"]:
        assert 0 <= point["v"] <= 100, f"RSI 범위 벗어남: {point['v']}"


@pytest.mark.asyncio
async def test_indicators_bollinger_order(client: AsyncClient) -> None:
    """볼린저 upper >= mid >= lower."""
    resp = await client.get("/market/symbol/yahoo/AAPL/indicators")
    data = resp.json()
    bb = data["bollinger"]
    for u, m, lo in zip(bb["upper"], bb["mid"], bb["lower"]):
        assert u["v"] >= m["v"] >= lo["v"], f"볼린저 역전: {u['v']} {m['v']} {lo['v']}"


@pytest.mark.asyncio
async def test_indicators_macd_histogram(client: AsyncClient) -> None:
    """MACD histogram = macd - signal (오차 1e-4 이내)."""
    resp = await client.get("/market/symbol/yahoo/AAPL/indicators")
    data = resp.json()
    for point in data["macd"]:
        expected = round(point["macd"] - point["signal"], 4)
        actual = point["histogram"]
        assert abs(expected - actual) < 1e-3, f"히스토그램 불일치: {expected} vs {actual}"


@pytest.mark.asyncio
async def test_indicators_stochastic_range(client: AsyncClient) -> None:
    """스토캐스틱 K, D 는 0~100 범위."""
    resp = await client.get("/market/symbol/upbit/KRW-BTC/indicators")
    data = resp.json()
    for point in data["stochastic"]:
        assert 0 <= point["k"] <= 100
        assert 0 <= point["d"] <= 100


@pytest.mark.asyncio
async def test_indicators_custom_period(client: AsyncClient) -> None:
    resp = await client.get("/market/symbol/binance/BTCUSDT/indicators?period=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == 30
