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


# ──────────────────────── stub quote / ohlc 테스트 ────────────────────────────


@pytest.fixture()
def mock_yf_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """yfinance executor 호출을 실패시켜 stub 폴백 경로를 강제한다."""
    import app.services.market.naver_kr as naver_mod

    def _fail_quote(yf_symbol: str) -> None:  # type: ignore[return]
        raise RuntimeError("yfinance mock failure")

    def _fail_ohlc(yf_symbol: str, interval: str, limit: int) -> list:  # type: ignore[return]
        raise RuntimeError("yfinance mock failure")

    monkeypatch.setattr(naver_mod, "_fetch_yf_quote_sync", _fail_quote)
    monkeypatch.setattr(naver_mod, "_fetch_yf_ohlc_sync", _fail_ohlc)


class TestNaverStubQuote:
    @pytest.mark.asyncio
    async def test_samsung_price_is_meaningful(self, mock_yf_failure: None):
        """삼성전자(005930) stub quote 가 1.0 이 아닌 실제 시세 근사값을 반환 (yfinance 실패 → stub 폴백)."""
        adapter = NaverKrAdapter()
        quote = await adapter.fetch_quote("005930")

        assert quote.symbol == "005930"
        assert quote.market == "naver_kr"
        assert quote.currency == "KRW"
        assert quote.price == 72000.0, f"삼성전자 가격이 stub 값과 다름: {quote.price}"
        assert abs(quote.change_pct - 0.56) < 0.01
        assert quote.volume is not None and quote.volume > 0

    @pytest.mark.asyncio
    async def test_all_stub_symbols_have_positive_price(self, mock_yf_failure: None):
        """_STUB_QUOTES 의 모든 종목 price > 0, volume > 0 (stub 폴백)."""
        adapter = NaverKrAdapter()
        for symbol in ("005930", "000660", "035420", "035720", "005380"):
            quote = await adapter.fetch_quote(symbol)
            assert quote.price > 1.0, f"{symbol} price 가 1.0 이하: {quote.price}"
            assert quote.volume is not None and quote.volume > 0

    @pytest.mark.asyncio
    async def test_unknown_symbol_fallback(self, mock_yf_failure: None):
        """_STUB_QUOTES 에 없는 종목은 _DEFAULT_STUB_PRICE(50000.0) + 0 변동 (yfinance 실패 → stub)."""
        adapter = NaverKrAdapter()
        quote = await adapter.fetch_quote("999999")

        assert quote.price == 50000.0
        assert quote.change == 0.0
        assert quote.change_pct == 0.0
        assert quote.volume == 500000.0

    @pytest.mark.asyncio
    async def test_quote_timestamp_is_iso8601(self, mock_yf_failure: None):
        """timestamp 필드가 ISO-8601 형식."""
        from datetime import datetime

        adapter = NaverKrAdapter()
        quote = await adapter.fetch_quote("005930")
        # 파싱 가능 여부로 검증
        dt = datetime.fromisoformat(quote.timestamp.replace("Z", "+00:00"))
        assert dt.year >= 2024


class TestNaverStubOhlc:
    @pytest.mark.asyncio
    async def test_samsung_ohlc_returns_100_bars(self, mock_yf_failure: None):
        """삼성전자 stub OHLC 가 100개 bar 를 반환 (yfinance 실패 → stub 폴백)."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930", interval="1d", limit=100)

        assert len(bars) == 100

    @pytest.mark.asyncio
    async def test_ohlc_price_range_reasonable(self, mock_yf_failure: None):
        """삼성전자 OHLC close 가 합리적 범위 (stub base 72000 ±30%) 내에 있음."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930")

        for bar in bars:
            assert bar.close > 0
            # ±2% 랜덤워크 100일 → σ≈20%, 99% CI ≈ ±60%. base 72000 기준 28800~115200
            # md5 결정론 시드라 PYTHONHASHSEED 무관 — 한번 통과하면 영구 통과
            assert 28000 <= bar.close <= 120000, f"close={bar.close} 범위 이탈"

    @pytest.mark.asyncio
    async def test_ohlc_high_low_invariant(self, mock_yf_failure: None):
        """모든 bar 에서 high >= max(open, close) >= min(open, close) >= low."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930")

        for bar in bars:
            assert bar.high >= bar.open
            assert bar.high >= bar.close
            assert bar.low <= bar.open
            assert bar.low <= bar.close

    @pytest.mark.asyncio
    async def test_ohlc_volume_positive(self, mock_yf_failure: None):
        """모든 bar volume > 0 (stub 폴백)."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930")

        for bar in bars:
            assert bar.volume is not None and bar.volume > 0

    @pytest.mark.asyncio
    async def test_ohlc_reproducible(self, mock_yf_failure: None):
        """동일 심볼에 대해 두 번 호출해도 동일한 결과 (stub 폴백 시드 고정)."""
        from app.services.market.yf_cache import yf_cache_clear

        yf_cache_clear()
        adapter = NaverKrAdapter()
        bars_a = await adapter.fetch_ohlc("005930")
        yf_cache_clear()
        bars_b = await adapter.fetch_ohlc("005930")

        # close 시퀀스 비교 (랜덤워크 시드가 같으면 동일해야 함)
        closes_a = [b.close for b in bars_a]
        closes_b = [b.close for b in bars_b]
        assert closes_a == closes_b, "동일 시드인데 결과가 다름"

    @pytest.mark.asyncio
    async def test_ohlc_different_symbols_differ(self, mock_yf_failure: None):
        """서로 다른 종목은 다른 OHLC 시퀀스를 생성."""
        adapter = NaverKrAdapter()
        bars_samsung = await adapter.fetch_ohlc("005930")
        bars_kakao = await adapter.fetch_ohlc("035720")

        closes_samsung = [b.close for b in bars_samsung]
        closes_kakao = [b.close for b in bars_kakao]
        # 완전히 같을 가능성은 통계적으로 0에 가까움
        assert closes_samsung != closes_kakao

    @pytest.mark.asyncio
    async def test_ohlc_unknown_symbol_fallback(self, mock_yf_failure: None):
        """_STUB_QUOTES 에 없는 종목도 100개 bar 를 반환하고 close > 0 (stub 폴백)."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("999999")

        assert len(bars) == 100
        for bar in bars:
            assert bar.close > 0

    @pytest.mark.asyncio
    async def test_ohlc_ts_format(self, mock_yf_failure: None):
        """ts 필드가 ISO-8601 파싱 가능."""
        from datetime import datetime

        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930")

        for bar in bars:
            dt = datetime.fromisoformat(bar.ts)
            assert dt.year >= 2024

    @pytest.mark.asyncio
    async def test_ohlc_chronological_order(self, mock_yf_failure: None):
        """bars 가 오래된 날짜 → 최신 날짜 순으로 정렬."""
        adapter = NaverKrAdapter()
        bars = await adapter.fetch_ohlc("005930")

        tss = [b.ts for b in bars]
        assert tss == sorted(tss), "OHLC 가 시간 순 정렬되지 않음"
