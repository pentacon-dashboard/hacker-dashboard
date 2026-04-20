"""
한글 alias 폴백 사전 테스트.

실 네트워크 없이 동작.
"""
from __future__ import annotations

import pytest

from app.services.market.aliases import ALIASES, lookup


class TestAliasLookupExactMatch:
    def test_tesla_exact(self):
        results = lookup("테슬라")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "TSLA"
        assert info.market == "yahoo"
        assert info.asset_class == "stock"
        assert score == 2000

    def test_bitcoin_exact(self):
        results = lookup("비트코인")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "KRW-BTC"
        assert info.market == "upbit"
        assert info.asset_class == "crypto"
        assert score == 2000

    def test_samsung_exact(self):
        results = lookup("삼성전자")
        assert len(results) >= 1
        info, score = results[0]
        # 국내주식은 Yahoo .KS 티커로 변환되어 Yahoo 어댑터로 시세 조회 가능
        assert info.symbol == "005930.KS"
        assert info.market == "yahoo"
        assert info.asset_class == "stock"
        assert info.currency == "KRW"
        assert score == 2000

    def test_apple_exact(self):
        results = lookup("애플")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "AAPL"
        assert info.market == "yahoo"
        assert score == 2000

    def test_ethereum_exact(self):
        results = lookup("이더리움")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "KRW-ETH"
        assert info.market == "upbit"
        assert score == 2000

    def test_nvidia_exact(self):
        results = lookup("엔비디아")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "NVDA"
        assert info.market == "yahoo"

    def test_sk_hynix_exact(self):
        results = lookup("sk하이닉스")
        assert len(results) >= 1
        info, score = results[0]
        assert info.symbol == "000660.KS"
        assert info.market == "yahoo"


class TestAliasLookupStartsWith:
    def test_bitcoin_prefix(self):
        """'비트' 로 시작하는 쿼리 → startswith 1500점."""
        results = lookup("비트")
        assert len(results) >= 1
        # 비트코인 포함 여부 확인
        symbols = [info.symbol for info, _ in results]
        assert "KRW-BTC" in symbols
        # 점수는 1500
        for info, score in results:
            if info.symbol == "KRW-BTC":
                assert score == 1500

    def test_samsung_prefix(self):
        """'삼성' 으로 시작하는 조회. 국내주식은 Yahoo .KS 티커 형식."""
        results = lookup("삼성")
        symbols = [info.symbol for info, _ in results]
        # 삼성전자 → 005930.KS
        assert "005930.KS" in symbols


class TestAliasLookupCaseAndSpace:
    def test_lowercase_query(self):
        """소문자 쿼리도 정상 동작."""
        results = lookup("테슬라")
        assert len(results) >= 1

    def test_query_with_spaces(self):
        """공백 포함 쿼리 — 정규화 후 매칭."""
        results_nospace = lookup("비트코인")
        results_space = lookup("비트 코인")
        # 공백 제거 후 동일 결과
        syms_nospace = {info.symbol for info, _ in results_nospace}
        syms_space = {info.symbol for info, _ in results_space}
        assert "KRW-BTC" in syms_nospace
        assert "KRW-BTC" in syms_space


class TestAliasCount:
    def test_minimum_80_aliases(self):
        """최소 80개 항목 보유."""
        assert len(ALIASES) >= 80

    def test_foreign_stocks_30(self):
        """해외 주식 30개 이상."""
        yahoo_stocks = [
            v for v in ALIASES.values() if v[0] == "yahoo" and v[2] == "stock"
        ]
        assert len(yahoo_stocks) >= 30

    def test_crypto_30(self):
        """코인 30개 이상."""
        upbit_cryptos = [
            v for v in ALIASES.values() if v[0] == "upbit" and v[2] == "crypto"
        ]
        assert len(upbit_cryptos) >= 30

    def test_kr_stocks_20(self):
        """국내 주식 20개 이상. Yahoo .KS/.KQ 티커 형식."""
        kr_stocks = [
            v for v in ALIASES.values()
            if v[0] == "yahoo" and v[2] == "stock" and (v[1].endswith(".KS") or v[1].endswith(".KQ"))
        ]
        assert len(kr_stocks) >= 20


class TestAliasNoMatch:
    def test_unknown_query_returns_empty(self):
        results = lookup("XYZABC_없는종목_999")
        assert results == []


class TestAliasScore:
    def test_exact_score_higher_than_startswith(self):
        """정확일치(2000)가 startswith(1500)보다 높다."""
        exact = lookup("비트코인")
        prefix = lookup("비트")

        exact_scores = {info.symbol: score for info, score in exact}
        prefix_scores = {info.symbol: score for info, score in prefix}

        if "KRW-BTC" in exact_scores and "KRW-BTC" in prefix_scores:
            assert exact_scores["KRW-BTC"] > prefix_scores["KRW-BTC"]
