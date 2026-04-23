"""
Upbit 랭킹 점수 테스트.

respx 로 Upbit API 응답 모킹. 랭킹 우선순위 검증.
"""
from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.market.base import set_http_client
from app.services.market.upbit import UpbitAdapter, _score_upbit

# 샘플 마켓 목록
_MARKET_ALL_DATA = [
    {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
    {"market": "KRW-BCH", "korean_name": "비트코인 캐시", "english_name": "Bitcoin Cash"},
    {"market": "KRW-BTG", "korean_name": "비트코인 골드", "english_name": "Bitcoin Gold"},
    {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
    {"market": "KRW-XRP", "korean_name": "리플", "english_name": "Ripple"},
    {"market": "KRW-SOL", "korean_name": "솔라나", "english_name": "Solana"},
    {"market": "BTC-XRP", "korean_name": "리플", "english_name": "Ripple"},
    {"market": "BTC-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
]


@pytest.fixture(autouse=True)
def inject_http_client(respx_mock):
    client = AsyncClient()
    set_http_client(client)
    yield
    set_http_client(None)


class TestScoreFunction:
    def test_symbol_exact_match(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "KRW-BTC")
        assert score >= 1000

    def test_base_symbol_exact_match(self):
        """KRW-BTC 에서 BTC 로 검색 시 base symbol 정확일치 950점."""
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "BTC")
        assert score >= 950

    def test_korean_exact_match(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "비트코인")
        assert score >= 900

    def test_english_exact_match(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "Bitcoin")
        assert score >= 850

    def test_symbol_startswith(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "KRW")
        assert score >= 500

    def test_korean_startswith(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "비트")
        assert score >= 400

    def test_english_startswith(self):
        item = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        score = _score_upbit(item, "Bit")
        assert score >= 350

    def test_substring_match(self):
        item = {"market": "KRW-BCH", "korean_name": "비트코인 캐시", "english_name": "Bitcoin Cash"}
        score = _score_upbit(item, "코인")
        assert score >= 100

    def test_krw_bonus(self):
        item_krw = {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"}
        # 동일 조건에서 KRW 마켓이 보너스 +50
        score_krw = _score_upbit(item_krw, "Bitcoin")
        score_btc_pair = _score_upbit(
            {"market": "BTC-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
            "Bitcoin",
        )
        assert score_krw > score_btc_pair

    def test_no_match_returns_zero(self):
        item = {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"}
        score = _score_upbit(item, "TSLA")
        assert score == 0


class TestUpbitSearchRanking:
    @respx.mock
    @pytest.mark.asyncio
    async def test_bitcoin_korean_search_btc_first(self):
        """'비트코인' 검색 시 KRW-BTC(정확일치)가 KRW-BCH(부분일치)보다 상위."""
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=_MARKET_ALL_DATA)
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("비트코인")

        assert len(results) >= 1
        assert results[0].symbol == "KRW-BTC", (
            f"KRW-BTC가 최상위여야 하는데 {results[0].symbol} 이 반환됨"
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_btc_exact_match_first(self):
        """'BTC' 검색 시 KRW-BTC 정확일치 심볼이 최상위."""
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=_MARKET_ALL_DATA)
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("BTC")

        assert len(results) >= 1
        # KRW-BTC 는 market_id 에 "BTC" 포함, KRW 마켓 보너스 → 최상위
        symbols = [r.symbol for r in results]
        assert "KRW-BTC" in symbols
        assert symbols.index("KRW-BTC") == 0 or results[0].symbol.endswith("BTC")

    @respx.mock
    @pytest.mark.asyncio
    async def test_ethereum_search(self):
        """'이더리움' 검색 시 KRW-ETH 포함."""
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=_MARKET_ALL_DATA)
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("이더리움")

        symbols = [r.symbol for r in results]
        assert "KRW-ETH" in symbols
        # KRW 마켓이 BTC 마켓보다 상위
        krw_idx = symbols.index("KRW-ETH")
        btc_idx = symbols.index("BTC-ETH") if "BTC-ETH" in symbols else 999
        assert krw_idx < btc_idx

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_20_results(self):
        """최대 20개 결과만 반환."""
        # 30개 항목 생성
        many_items = [
            {"market": f"KRW-COIN{i}", "korean_name": f"코인{i}", "english_name": f"Coin{i}"}
            for i in range(30)
        ]
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=many_items)
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("코인")
        assert len(results) <= 20

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        """매칭 없으면 빈 리스트."""
        respx.get("https://api.upbit.com/v1/market/all").mock(
            return_value=Response(200, json=_MARKET_ALL_DATA)
        )
        adapter = UpbitAdapter()
        results = await adapter.search_symbols("TSLA_NO_MATCH_XYZ")
        assert results == []
