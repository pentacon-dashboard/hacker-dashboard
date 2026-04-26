"""
워치리스트 서비스 단위 테스트 — Sprint-08 B-2.

compute_summary, generate_popular_stub, generate_gainers_losers_stub, sparkline_7d
"""

from __future__ import annotations

from app.services.watchlist import (
    compute_summary,
    generate_gainers_losers_stub,
    generate_popular_stub,
    sparkline_7d,
)


class TestComputeSummary:
    def test_empty_list_returns_zero_summary(self) -> None:
        result = compute_summary([])
        assert result.watched_count == 0
        assert result.top_gainer_name == "-"
        assert result.top_gainer_pct == "+0.00"

    def test_all_gainers(self) -> None:
        items = [
            {"name": "AAPL", "change_pct": "+3.00"},
            {"name": "NVDA", "change_pct": "+5.00"},
        ]
        result = compute_summary(items)
        assert result.watched_count == 2
        assert result.top_gainer_name == "NVDA"
        assert result.top_gainer_pct == "+5.00"
        # 상승만 있으므로 down_avg 는 0
        assert result.down_avg_pct == "-0.00"

    def test_all_losers(self) -> None:
        items = [
            {"name": "TSLA", "change_pct": "-2.00"},
            {"name": "META", "change_pct": "-4.00"},
        ]
        result = compute_summary(items)
        assert result.watched_count == 2
        # 모두 하락 → up_avg 는 0
        assert result.up_avg_pct == "+0.00"
        assert "-" in result.down_avg_pct

    def test_mixed_returns_correct_stats(self) -> None:
        items = [
            {"name": "AAPL", "change_pct": "+3.00"},
            {"name": "TSLA", "change_pct": "-2.00"},
            {"name": "NVDA", "change_pct": "+6.00"},
            {"name": "META", "change_pct": "-1.00"},
        ]
        result = compute_summary(items)
        assert result.watched_count == 4
        assert result.top_gainer_name == "NVDA"
        assert result.top_gainer_pct == "+6.00"
        # up_avg = (3+6)/2 = 4.50
        assert result.up_avg_pct == "+4.50"

    def test_zero_change_is_treated_as_gainer(self) -> None:
        items = [{"name": "X", "change_pct": "0.00"}]
        result = compute_summary(items)
        assert result.up_avg_pct == "+0.00"
        assert result.top_gainer_pct == "+0.00"


class TestStubGenerators:
    def test_popular_returns_5_items(self) -> None:
        result = generate_popular_stub()
        assert len(result) == 5

    def test_popular_has_views_24h(self) -> None:
        result = generate_popular_stub()
        assert all(item.views_24h is not None and item.views_24h > 0 for item in result)

    def test_popular_ranks_are_1_to_5(self) -> None:
        result = generate_popular_stub()
        ranks = [item.rank for item in result]
        assert ranks == list(range(1, 6))

    def test_gainers_losers_has_both_keys(self) -> None:
        result = generate_gainers_losers_stub()
        assert "gainers" in result
        assert "losers" in result

    def test_gainers_losers_each_5_items(self) -> None:
        result = generate_gainers_losers_stub()
        assert len(result["gainers"]) == 5
        assert len(result["losers"]) == 5

    def test_gainers_have_positive_pct(self) -> None:
        result = generate_gainers_losers_stub()
        for item in result["gainers"]:
            assert item.change_pct.startswith("+"), f"{item.change_pct} 는 양수여야 함"

    def test_losers_have_negative_pct(self) -> None:
        result = generate_gainers_losers_stub()
        for item in result["losers"]:
            assert item.change_pct.startswith("-"), f"{item.change_pct} 는 음수여야 함"


class TestSparkline:
    def test_returns_7_values(self) -> None:
        result = sparkline_7d("upbit", "KRW-BTC")
        assert len(result) == 7

    def test_deterministic(self) -> None:
        """같은 입력이면 항상 같은 결과."""
        r1 = sparkline_7d("yahoo", "AAPL")
        r2 = sparkline_7d("yahoo", "AAPL")
        assert r1 == r2

    def test_different_inputs_different_outputs(self) -> None:
        r1 = sparkline_7d("yahoo", "AAPL")
        r2 = sparkline_7d("binance", "BTCUSDT")
        assert r1 != r2

    def test_values_are_positive(self) -> None:
        result = sparkline_7d("upbit", "KRW-ETH")
        assert all(v > 0 for v in result)
