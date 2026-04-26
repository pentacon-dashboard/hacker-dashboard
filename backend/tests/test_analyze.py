from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_returns_200(client: AsyncClient) -> None:
    payload = {
        "data": [{"symbol": "AAPL", "price": 180.0, "date": "2024-01-01"}],
        "query": "주가 추세 분석",
        "asset_class_hint": "stock",
    }
    response = await client.post("/analyze", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_analyze_response_schema(client: AsyncClient) -> None:
    payload = {
        "data": [{"symbol": "BTC-USD", "price": 50000.0}],
        "asset_class_hint": "crypto",
    }
    response = await client.post("/analyze", json=payload)
    body = response.json()

    assert "request_id" in body
    assert "status" in body
    assert "meta" in body
    assert body["meta"]["asset_class"] == "crypto"
    assert "router_reason" in body["meta"]
    assert "gates" in body["meta"]


@pytest.mark.asyncio
async def test_analyze_gates_all_ok(client: AsyncClient, fake_llm_client) -> None:
    payload = {"data": [{"price": 100.0}]}
    response = await client.post("/analyze", json=payload)
    body = response.json()

    gates = body["meta"]["gates"]
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"] == "pass"
    assert gates["critique_gate"] == "pass"


@pytest.mark.asyncio
async def test_analyze_without_hint_defaults_to_stock(
    client: AsyncClient, fake_llm_client: Any
) -> None:
    """hint 없고 heuristic 미매칭 시 LLM Router 가 기본값 "stock" 을 반환해야 한다.

    fake_llm_client 의 router 응답이 없으면 extract_json({}) → asset_class="stock"(기본값).
    Redis 캐시에 이전 실행 결과가 남아있을 수 있으므로 LRU 전용 모드로 캐시를 격리한다.
    """
    from app.services import analyze_cache as _ac

    _ac.reset_for_testing()
    _ac._redis_available = False  # 이전 Redis 잔여 데이터 방지

    payload = {"data": [{"price": 100.0}]}
    response = await client.post("/analyze", json=payload)
    body = response.json()
    assert body["meta"]["asset_class"] == "stock"


@pytest.mark.asyncio
async def test_market_symbols(client: AsyncClient) -> None:
    response = await client.get("/market/symbols")
    assert response.status_code == 200
    symbols = response.json()
    assert isinstance(symbols, list)
    assert len(symbols) > 0
    assert "symbol" in symbols[0]
    assert "asset_class" in symbols[0]


@pytest.mark.asyncio
async def test_market_quote(client: AsyncClient) -> None:
    response = await client.get("/market/quotes/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["price"] > 0
