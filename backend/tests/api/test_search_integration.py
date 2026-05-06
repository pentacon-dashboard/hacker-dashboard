"""
통합 검색 API 한글 쿼리 테스트.

respx 로 외부 어댑터를 모킹. 한글 쿼리 3종 → 상위 결과 검증.
"""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.market.base import set_http_client
from app.services.market.cache import set_redis

# ── 픽스처 ──────────────────────────────────────────────────────────────


@pytest.fixture
async def api_client():
    """FastAPI test client."""
    from httpx import ASGITransport

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def inject_http_and_redis(respx_mock):
    """respx intercept + Redis 비활성화."""
    client = AsyncClient()
    set_http_client(client)
    set_redis(None)
    yield
    set_http_client(None)
    set_redis(None)


def _mock_upbit_all():
    """Upbit market/all 모킹."""
    respx.get("https://api.upbit.com/v1/market/all").mock(
        return_value=Response(
            200,
            json=[
                {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
                {
                    "market": "KRW-BCH",
                    "korean_name": "비트코인 캐시",
                    "english_name": "Bitcoin Cash",
                },
                {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
                {"market": "KRW-SOL", "korean_name": "솔라나", "english_name": "Solana"},
                {"market": "KRW-XRP", "korean_name": "리플", "english_name": "Ripple"},
            ],
        )
    )


def _mock_naver_empty():
    """Naver 검색 빈 응답 모킹."""
    respx.get("https://m.stock.naver.com/api/search/all").mock(
        return_value=Response(200, json={"stocks": {"items": []}, "worldStocks": {"items": []}})
    )


def _mock_naver_samsung():
    """Naver 삼성전자 검색 응답 모킹."""
    respx.get("https://m.stock.naver.com/api/search/all").mock(
        return_value=Response(
            200,
            json={
                "stocks": {
                    "items": [
                        {"itemCode": "005930", "stockName": "삼성전자", "nationType": "KR"},
                    ]
                },
                "worldStocks": {"items": []},
            },
        )
    )


def _mock_yahoo_empty():
    """Yahoo 검색 빈 응답 모킹."""
    respx.get("https://query1.finance.yahoo.com/v1/finance/search").mock(
        return_value=Response(200, json={"quotes": []})
    )


# ── 테스트: 비트코인 ─────────────────────────────────────────────────────


class TestSearchBitcoin:
    @respx.mock
    @pytest.mark.asyncio
    async def test_bitcoin_search_krw_btc_in_top3(self, api_client):
        """'비트코인' 검색 시 KRW-BTC 가 상위 3개 안에 포함."""
        _mock_upbit_all()
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "비트코인"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

        top3_symbols = [item["symbol"] for item in data[:3]]
        assert "KRW-BTC" in top3_symbols, f"KRW-BTC 가 top3 에 없음: {top3_symbols}"

    @respx.mock
    @pytest.mark.asyncio
    async def test_bitcoin_cash_not_first(self, api_client):
        """'비트코인' 검색 시 KRW-BCH(비트코인 캐시)가 KRW-BTC 보다 후순위."""
        _mock_upbit_all()
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "비트코인"})
        assert resp.status_code == 200
        data = resp.json()
        symbols = [item["symbol"] for item in data]

        if "KRW-BTC" in symbols and "KRW-BCH" in symbols:
            assert symbols.index("KRW-BTC") < symbols.index("KRW-BCH"), (
                "KRW-BTC 이 KRW-BCH 보다 먼저 와야 함"
            )

    @respx.mock
    @pytest.mark.asyncio
    async def test_score_field_not_in_response(self, api_client):
        """응답에 score 필드 없음."""
        _mock_upbit_all()
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "비트코인"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert "score" not in item, "score 필드가 응답에 노출되면 안 됨"


# ── 테스트: 테슬라 ─────────────────────────────────────────────────────


class TestSearchTesla:
    @respx.mock
    @pytest.mark.asyncio
    async def test_tesla_alias_in_top1(self, api_client):
        """'테슬라' 검색 시 alias(TSLA, yahoo)가 최상위."""
        _mock_upbit_all()
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "테슬라"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["symbol"] == "TSLA"
        assert data[0]["market"] == "yahoo"

    @respx.mock
    @pytest.mark.asyncio
    async def test_tesla_response_schema(self, api_client):
        """응답 스키마 검증 — SymbolInfo 필드 포함."""
        _mock_upbit_all()
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "테슬라"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        tsla = data[0]
        assert "symbol" in tsla
        assert "name" in tsla
        assert "asset_class" in tsla
        assert "market" in tsla


# ── 테스트: 삼성전자 ───────────────────────────────────────────────────


class TestSearchSamsung:
    @respx.mock
    @pytest.mark.asyncio
    async def test_samsung_naver_symbol_in_results(self, api_client):
        """'삼성전자' 검색 시 naver_kr 005930 이 반환됨."""
        _mock_upbit_all()
        _mock_naver_samsung()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "삼성전자"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

        assert any(
            item["market"] == "naver_kr" and item["symbol"] == "005930"
            for item in data
        ), f"naver_kr 005930 결과 없음: {data}"

    @respx.mock
    @pytest.mark.asyncio
    async def test_samsung_market_prefers_naver_kr(self, api_client):
        """삼성전자 검색 결과는 Yahoo .KS 대신 naver_kr 6자리 코드를 우선한다."""
        _mock_upbit_all()
        _mock_naver_samsung()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "삼성전자"})
        assert resp.status_code == 200
        data = resp.json()

        samsung_items = [item for item in data if "005930" in item["symbol"]]
        assert len(samsung_items) >= 1
        assert samsung_items[0]["market"] == "naver_kr"
        assert samsung_items[0]["symbol"] == "005930"
        # dedupe 후 삼성전자 canonical 결과는 한 번만 등장
        assert len(samsung_items) == 1


# ── 테스트: 최대 50개 ─────────────────────────────────────────────────


class TestSearchLimit:
    @respx.mock
    @pytest.mark.asyncio
    async def test_max_50_results(self, api_client):
        """결과 최대 50개."""
        # 많은 결과 반환하도록 설정
        many_items = [
            {
                "market": f"KRW-COIN{i}",
                "korean_name": f"테스트코인{i}",
                "english_name": f"TestCoin{i}",
            }
            for i in range(100)
        ]
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=many_items)
        )
        _mock_naver_empty()
        _mock_yahoo_empty()

        resp = await api_client.get("/market/symbols/search", params={"q": "테스트코인"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 50

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_query_error(self, api_client):
        """빈 쿼리는 422 반환."""
        resp = await api_client.get("/market/symbols/search", params={"q": ""})
        assert resp.status_code == 422
