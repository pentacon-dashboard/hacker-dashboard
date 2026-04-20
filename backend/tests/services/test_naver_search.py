"""
Naver KR 어댑터 검색 단위 테스트.

respx 로 네이버 API 응답을 모킹. 실 네트워크 없이 동작.
"""
from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.market.base import set_http_client
from app.services.market.naver_kr import NaverKrAdapter


@pytest.fixture(autouse=True)
def inject_http_client(respx_mock):
    client = AsyncClient()
    set_http_client(client)
    yield
    set_http_client(None)


# 샘플 응답 JSON — 실제 m.stock.naver.com 응답 구조 기반
_SAMSUNG_RESPONSE = {
    "stocks": {
        "items": [
            {
                "itemCode": "005930",
                "stockName": "삼성전자",
                "nationType": "KR",
                "market": "KRX",
            },
            {
                "itemCode": "005935",
                "stockName": "삼성전자우",
                "nationType": "KR",
                "market": "KRX",
            },
        ]
    },
    "worldStocks": {"items": []},
    "etfs": {"items": []},
}

_TESLA_RESPONSE = {
    "stocks": {"items": []},
    "worldStocks": {
        "items": [
            {
                "reutersCode": "TSLA",
                "stockName": "테슬라",
                "nationType": "US",
                "market": "NASDAQ",
            }
        ]
    },
    "etfs": {"items": []},
}

_BITCOIN_RESPONSE = {
    "stocks": {"items": []},
    "worldStocks": {"items": []},
    "etfs": {"items": []},
    # coins 섹션은 의도적으로 skip (KRW-XXX 변환 불확실)
    "coins": {
        "items": [
            {
                "itemCode": "BTC",
                "stockName": "비트코인",
                "nationType": "COIN",
            }
        ]
    },
}


class TestNaverSearchSamsung:
    @respx.mock
    @pytest.mark.asyncio
    async def test_samsung_mapped_to_yahoo(self):
        """국내 종목은 Yahoo Finance 티커(.KS)로 변환되어 반환."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=_SAMSUNG_RESPONSE)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")

        assert len(results) >= 1
        # 005930.KS 또는 005930.KQ 형식으로 반환
        yahoo_symbols = [r.symbol for r in results if r.market == "yahoo"]
        assert len(yahoo_symbols) >= 1
        assert any(s.startswith("005930") for s in yahoo_symbols)

    @respx.mock
    @pytest.mark.asyncio
    async def test_samsung_market_is_yahoo(self):
        """국내 종목의 market='yahoo' — 워치리스트 후 시세 조회 가능."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=_SAMSUNG_RESPONSE)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")

        samsung = next(r for r in results if "005930" in r.symbol)
        assert samsung.market == "yahoo", f"국내 종목은 yahoo 어댑터여야 함, got: {samsung.market}"
        assert samsung.symbol.endswith(".KS") or samsung.symbol.endswith(".KQ")
        assert samsung.currency == "KRW"
        assert samsung.asset_class == "stock"

    @respx.mock
    @pytest.mark.asyncio
    async def test_samsung_has_name(self):
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=_SAMSUNG_RESPONSE)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")
        samsung = next(r for r in results if "005930" in r.symbol)
        assert "삼성전자" in samsung.name


class TestNaverSearchTesla:
    @respx.mock
    @pytest.mark.asyncio
    async def test_tesla_parsed_as_yahoo(self):
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=_TESLA_RESPONSE)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("테슬라")

        assert len(results) >= 1
        tsla = next((r for r in results if r.symbol == "TSLA"), None)
        assert tsla is not None
        # 미국 주식은 yahoo 마켓으로 라우팅
        assert tsla.market == "yahoo"
        assert tsla.currency == "USD"


class TestNaverSearchBitcoin:
    @respx.mock
    @pytest.mark.asyncio
    async def test_bitcoin_coins_section_skipped(self):
        """coins 섹션은 KRW-XXX 변환 불확실로 skip — 빈 리스트 반환."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=_BITCOIN_RESPONSE)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("비트코인")
        # coins 섹션은 파싱하지 않으므로 naver_kr 결과 없음
        naver_coins = [r for r in results if r.market == "naver_kr" and r.asset_class == "crypto"]
        assert naver_coins == []


class TestNaverSearchErrorHandling:
    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error_returns_empty(self):
        """네트워크 에러 시 빈 리스트 반환 (silent fail)."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            side_effect=Exception("connection refused")
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")
        assert results == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        """HTTP 500 에러 시 빈 리스트 반환."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")
        assert results == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_malformed_json_returns_empty(self):
        """응답이 dict 가 아닌 경우 빈 리스트 반환."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=[])  # list, not dict
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")
        assert results == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_sections_returns_empty(self):
        """섹션이 비어있으면 빈 리스트."""
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json={"stocks": {"items": []}, "worldStocks": {"items": []}})
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("없는종목xyz")
        assert results == []


class TestNaverDeduplication:
    @respx.mock
    @pytest.mark.asyncio
    async def test_deduplicate_same_symbol(self):
        """동일 (market, symbol) 중복 제거. 국내주식 → 005930.KS 형식."""
        dup_response = {
            "stocks": {
                "items": [
                    {"itemCode": "005930", "stockName": "삼성전자", "nationType": "KR"},
                    {"itemCode": "005930", "stockName": "삼성전자(중복)", "nationType": "KR"},
                ]
            }
        }
        respx.get("https://m.stock.naver.com/api/search/all").mock(
            return_value=Response(200, json=dup_response)
        )
        adapter = NaverKrAdapter()
        results = await adapter.search_symbols("삼성전자")
        symbols = [r.symbol for r in results]
        # 국내주식은 005930.KS 로 변환, 중복 제거 후 1개만
        assert symbols.count("005930.KS") == 1
