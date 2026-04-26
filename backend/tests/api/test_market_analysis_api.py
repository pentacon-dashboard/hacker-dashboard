"""
Market Analysis API 통합 테스트 — Sprint-08 B-4.

GET /market/indices
GET /market/sectors
GET /market/commodities
GET /market/world-heatmap

yfinance 실시간 경로를 None 반환으로 mock → stub 폴백 경로만 검증.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_yf_market(monkeypatch: pytest.MonkeyPatch) -> None:
    """yf_market 서비스 함수를 None 반환으로 stub — stub 폴백 경로 강제."""
    import app.services.market.yf_market as yf_mod

    async def _none() -> None:
        return None

    monkeypatch.setattr(yf_mod, "get_indices", _none)
    monkeypatch.setattr(yf_mod, "get_sectors", _none)
    monkeypatch.setattr(yf_mod, "get_commodities", _none)


@pytest.mark.asyncio
async def test_indices_returns_7_items(client: AsyncClient) -> None:
    resp = await client.get("/market/indices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7


@pytest.mark.asyncio
async def test_indices_schema(client: AsyncClient) -> None:
    resp = await client.get("/market/indices")
    for item in resp.json():
        assert "ticker" in item
        assert "display_name" in item
        assert "value" in item
        assert "change_pct" in item
        assert "change_abs" in item
        assert "sparkline_7d" in item
        assert isinstance(item["sparkline_7d"], list)
        assert len(item["sparkline_7d"]) == 7


@pytest.mark.asyncio
async def test_indices_includes_expected_tickers(client: AsyncClient) -> None:
    resp = await client.get("/market/indices")
    tickers = [item["ticker"] for item in resp.json()]
    assert "^GSPC" in tickers  # S&P 500
    assert "^KS11" in tickers  # KOSPI
    assert "^VIX" in tickers


@pytest.mark.asyncio
async def test_sectors_returns_11_items(client: AsyncClient) -> None:
    resp = await client.get("/market/sectors")
    assert resp.status_code == 200
    assert len(resp.json()) == 11


@pytest.mark.asyncio
async def test_sectors_schema(client: AsyncClient) -> None:
    resp = await client.get("/market/sectors")
    for item in resp.json():
        assert "name" in item
        assert "change_pct" in item
        assert "constituents" in item
        assert isinstance(item["constituents"], int)
        assert "leaders" in item
        assert isinstance(item["leaders"], list)


@pytest.mark.asyncio
async def test_commodities_returns_5_items(client: AsyncClient) -> None:
    resp = await client.get("/market/commodities")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


@pytest.mark.asyncio
async def test_commodities_schema(client: AsyncClient) -> None:
    resp = await client.get("/market/commodities")
    for item in resp.json():
        assert "symbol" in item
        assert "name" in item
        assert "price" in item
        assert "change_pct" in item
        assert "unit" in item


@pytest.mark.asyncio
async def test_commodities_includes_gold(client: AsyncClient) -> None:
    resp = await client.get("/market/commodities")
    symbols = [item["symbol"] for item in resp.json()]
    assert "GC=F" in symbols  # 금


@pytest.mark.asyncio
async def test_world_heatmap_returns_20_items(client: AsyncClient) -> None:
    resp = await client.get("/market/world-heatmap")
    assert resp.status_code == 200
    assert len(resp.json()) == 20


@pytest.mark.asyncio
async def test_world_heatmap_schema(client: AsyncClient) -> None:
    resp = await client.get("/market/world-heatmap")
    for item in resp.json():
        assert "country_code" in item
        assert "country_name" in item
        assert "change_pct" in item
        assert "market_cap_usd" in item
        # country_code 는 2자리 대문자여야 함
        assert len(item["country_code"]) == 2
        assert item["country_code"].isupper()


@pytest.mark.asyncio
async def test_world_heatmap_includes_major_countries(client: AsyncClient) -> None:
    resp = await client.get("/market/world-heatmap")
    codes = [item["country_code"] for item in resp.json()]
    for expected in ["US", "CN", "JP", "KR", "DE"]:
        assert expected in codes, f"{expected} 누락"
