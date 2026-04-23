"""
워치리스트 확장 API 통합 테스트 — Sprint-08 B-2.

GET /watchlist/summary
GET /watchlist/popular
GET /watchlist/gainers-losers
GET /market/watchlist/items  (pnl_7d 포함 여부 확인)
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.api import market as market_module


@pytest.fixture(autouse=True)
def reset_watchlist():
    """각 테스트 전 watchlist 스토어 초기화."""
    market_module._watchlist.clear()
    market_module._next_id = 1
    yield
    market_module._watchlist.clear()
    market_module._next_id = 1


# ──────────────── GET /watchlist/summary ────────────────

@pytest.mark.asyncio
async def test_summary_empty(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["watched_count"] == 0
    assert "up_avg_pct" in data
    assert "down_avg_pct" in data
    assert "top_gainer_name" in data
    assert "top_gainer_pct" in data


@pytest.mark.asyncio
async def test_summary_with_items(client: AsyncClient) -> None:
    """워치리스트에 아이템이 있으면 watched_count 가 증가."""
    await client.post("/market/watchlist/items", json={"market": "upbit", "code": "KRW-BTC"})
    await client.post("/market/watchlist/items", json={"market": "yahoo", "code": "AAPL"})

    resp = await client.get("/watchlist/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["watched_count"] == 2


# ──────────────── GET /watchlist/popular ────────────────

@pytest.mark.asyncio
async def test_popular_returns_5_items(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_popular_schema(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/popular")
    assert resp.status_code == 200
    for item in resp.json():
        assert "rank" in item
        assert "ticker" in item
        assert "name" in item
        assert "change_pct" in item
        assert "views_24h" in item


@pytest.mark.asyncio
async def test_popular_ranks_are_sequential(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/popular")
    ranks = [item["rank"] for item in resp.json()]
    assert ranks == list(range(1, 6))


# ──────────────── GET /watchlist/gainers-losers ────────────────

@pytest.mark.asyncio
async def test_gainers_losers_structure(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/gainers-losers")
    assert resp.status_code == 200
    data = resp.json()
    assert "gainers" in data
    assert "losers" in data
    assert len(data["gainers"]) == 5
    assert len(data["losers"]) == 5


@pytest.mark.asyncio
async def test_gainers_positive_pct(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/gainers-losers")
    for item in resp.json()["gainers"]:
        assert item["change_pct"].startswith("+"), f"Gainer pct should be positive: {item['change_pct']}"


@pytest.mark.asyncio
async def test_losers_negative_pct(client: AsyncClient) -> None:
    resp = await client.get("/watchlist/gainers-losers")
    for item in resp.json()["losers"]:
        assert item["change_pct"].startswith("-"), f"Loser pct should be negative: {item['change_pct']}"


# ──────────────── GET /market/watchlist/items (pnl_7d) ────────────────

@pytest.mark.asyncio
async def test_watchlist_items_include_pnl_7d(client: AsyncClient) -> None:
    """워치리스트 아이템에 pnl_7d 필드가 포함되어야 함."""
    await client.post("/market/watchlist/items", json={"market": "upbit", "code": "KRW-BTC"})

    resp = await client.get("/market/watchlist/items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert "pnl_7d" in item
    assert isinstance(item["pnl_7d"], list)
    assert len(item["pnl_7d"]) == 7


@pytest.mark.asyncio
async def test_watchlist_items_pnl_deterministic(client: AsyncClient) -> None:
    """같은 market/code 이면 pnl_7d 가 동일."""
    await client.post("/market/watchlist/items", json={"market": "yahoo", "code": "AAPL"})
    resp1 = await client.get("/market/watchlist/items")
    pnl1 = resp1.json()[0]["pnl_7d"]

    market_module._watchlist.clear()
    market_module._next_id = 1

    await client.post("/market/watchlist/items", json={"market": "yahoo", "code": "AAPL"})
    resp2 = await client.get("/market/watchlist/items")
    pnl2 = resp2.json()[0]["pnl_7d"]

    assert pnl1 == pnl2
