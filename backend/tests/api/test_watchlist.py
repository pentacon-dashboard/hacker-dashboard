"""
Watchlist CRUD API 테스트.

GET  /market/watchlist/items
POST /market/watchlist/items
DELETE /market/watchlist/items/{id}
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# watchlist 인-메모리 스토어 초기화 헬퍼
from app.api import market as market_module


@pytest.fixture(autouse=True)
def reset_watchlist():
    """각 테스트 전에 watchlist 스토어 초기화."""
    market_module._watchlist.clear()
    market_module._next_id = 1
    yield
    market_module._watchlist.clear()
    market_module._next_id = 1


@pytest.mark.asyncio
async def test_watchlist_empty(client: AsyncClient) -> None:
    resp = await client.get("/market/watchlist/items")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_watchlist_add(client: AsyncClient) -> None:
    body = {"market": "upbit", "code": "KRW-BTC", "memo": "테스트 메모"}
    resp = await client.post("/market/watchlist/items", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["market"] == "upbit"
    assert data["code"] == "KRW-BTC"
    assert data["memo"] == "테스트 메모"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_watchlist_list_after_add(client: AsyncClient) -> None:
    await client.post("/market/watchlist/items", json={"market": "binance", "code": "BTCUSDT"})
    await client.post("/market/watchlist/items", json={"market": "yahoo", "code": "AAPL"})

    resp = await client.get("/market/watchlist/items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    codes = [i["code"] for i in items]
    assert "BTCUSDT" in codes
    assert "AAPL" in codes


@pytest.mark.asyncio
async def test_watchlist_delete(client: AsyncClient) -> None:
    add_resp = await client.post(
        "/market/watchlist/items", json={"market": "upbit", "code": "KRW-ETH"}
    )
    item_id = add_resp.json()["id"]

    del_resp = await client.delete(f"/market/watchlist/items/{item_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/market/watchlist/items")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_watchlist_delete_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/market/watchlist/items/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_add_invalid_market(client: AsyncClient) -> None:
    resp = await client.post(
        "/market/watchlist/items", json={"market": "nonexistent", "code": "XXXYYY"}
    )
    assert resp.status_code == 422
