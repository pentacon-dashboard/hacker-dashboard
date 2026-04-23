"""
기술 지표 계산 단위 테스트 — Sprint-08 B-3.

calc_rsi, calc_macd, calc_bollinger, calc_stochastic 정확성 검증.
"""
from __future__ import annotations

import math

import pytest

from app.services.indicators import calc_bollinger, calc_macd, calc_rsi, calc_stochastic


# ──────────────── 공통 픽스처 ────────────────

def _make_closes(n: int = 50, base: float = 100.0, trend: float = 0.5) -> list[float]:
    """단조 상승 closes (RSI 계산 기준값 확인용)."""
    return [round(base + i * trend, 4) for i in range(n)]


def _make_alternating(n: int = 60) -> list[float]:
    """상승/하락 교대 패턴 (MACD 크로스 확인용)."""
    return [100.0 + math.sin(i * 0.3) * 5 for i in range(n)]


# ──────────────── RSI ────────────────

class TestCalcRsi:
    def test_returns_correct_length(self) -> None:
        closes = _make_closes(50)
        result = calc_rsi(closes, period=14)
        # RSI 계산: deltas = len(closes)-1 = 49, 반환 길이 = 49 - 14 = 35
        assert len(result) == len(closes) - 1 - 14

    def test_all_uptrend_rsi_near_100(self) -> None:
        """완전 상승 시 RSI 는 100 에 수렴."""
        closes = _make_closes(60, trend=1.0)
        result = calc_rsi(closes, period=14)
        assert result, "결과가 비어서는 안 됨"
        # 단조 상승이므로 RSI 가 95 이상이어야 함
        assert all(r > 90 for r in result), f"최소값: {min(result)}"

    def test_all_downtrend_rsi_near_0(self) -> None:
        """완전 하락 시 RSI 는 0 에 수렴."""
        closes = _make_closes(60, trend=-1.0)
        result = calc_rsi(closes, period=14)
        assert result, "결과가 비어서는 안 됨"
        assert all(r < 10 for r in result), f"최대값: {max(result)}"

    def test_insufficient_data_returns_empty(self) -> None:
        """데이터가 period 이하이면 빈 리스트."""
        result = calc_rsi([100.0, 101.0, 99.0], period=14)
        assert result == []

    def test_rsi_range_0_to_100(self) -> None:
        """RSI 는 항상 [0, 100] 범위."""
        closes = _make_alternating(80)
        result = calc_rsi(closes, period=14)
        assert all(0 <= r <= 100 for r in result)

    def test_hand_computed_simple_case(self) -> None:
        """단순 수동 계산 검증: 강한 상승 후 RSI 가 높아야 함."""
        closes = _make_closes(30, trend=1.0)  # 30개 단조 상승
        result = calc_rsi(closes, period=14)
        # deltas=29, rsi_values = 29-14 = 15개
        assert len(result) == 15
        assert all(r > 90 for r in result), f"최소값: {min(result)}"


# ──────────────── MACD ────────────────

class TestCalcMacd:
    def test_returns_three_lists(self) -> None:
        closes = _make_closes(80)
        macd, signal, hist = calc_macd(closes)
        assert len(macd) > 0
        assert len(macd) == len(signal) == len(hist)

    def test_insufficient_data_returns_empty(self) -> None:
        closes = _make_closes(20)  # slow=26 보다 적음
        macd, signal, hist = calc_macd(closes)
        assert macd == signal == hist == []

    def test_histogram_is_macd_minus_signal(self) -> None:
        closes = _make_alternating(80)
        macd, signal, hist = calc_macd(closes)
        for m, s, h in zip(macd, signal, hist):
            assert abs((m - s) - h) < 1e-4, f"히스토그램 불일치: {m} - {s} != {h}"

    def test_uptrend_positive_macd(self) -> None:
        """강한 상승 추세에서 MACD > 0 이어야 함."""
        closes = _make_closes(80, trend=2.0)
        macd, signal, hist = calc_macd(closes)
        # 후반부 대부분이 양수여야 함
        tail = macd[-10:]
        assert sum(1 for v in tail if v > 0) >= 8


# ──────────────── 볼린저 밴드 ────────────────

class TestCalcBollinger:
    def test_returns_three_lists(self) -> None:
        closes = _make_closes(50)
        upper, mid, lower = calc_bollinger(closes)
        assert len(upper) == len(mid) == len(lower)
        assert len(mid) == len(closes) - 20 + 1

    def test_upper_ge_mid_ge_lower(self) -> None:
        """upper >= mid >= lower 항상 성립."""
        closes = _make_alternating(60)
        upper, mid, lower = calc_bollinger(closes)
        for u, m, l in zip(upper, mid, lower):
            assert u >= m >= l, f"밴드 역전: {u} {m} {l}"

    def test_mid_is_rolling_mean(self) -> None:
        """mid 는 20일 이동평균이어야 함."""
        closes = list(range(1, 51))  # 1~50
        upper, mid, lower = calc_bollinger(closes, period=20)
        # 첫 mid: 평균(1~20) = 10.5
        expected_first_mid = sum(range(1, 21)) / 20
        assert abs(mid[0] - expected_first_mid) < 1e-4

    def test_insufficient_data_returns_empty(self) -> None:
        result = calc_bollinger([100.0] * 5, period=20)
        assert result == ([], [], [])

    def test_custom_k_widens_bands(self) -> None:
        closes = _make_alternating(60)
        _, _, lower2 = calc_bollinger(closes, k=2.0)
        _, _, lower3 = calc_bollinger(closes, k=3.0)
        # k=3 이 더 넓으므로 lower 가 더 낮아야 함
        assert all(l3 <= l2 for l3, l2 in zip(lower3, lower2))


# ──────────────── 스토캐스틱 ────────────────

class TestCalcStochastic:
    def _make_hls(self, n: int = 60) -> tuple[list[float], list[float], list[float]]:
        closes = _make_alternating(n)
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        return highs, lows, closes

    def test_returns_two_lists(self) -> None:
        highs, lows, closes = self._make_hls(80)
        k, d = calc_stochastic(highs, lows, closes)
        assert len(k) > 0
        assert len(k) == len(d)

    def test_range_0_to_100(self) -> None:
        highs, lows, closes = self._make_hls(80)
        k, d = calc_stochastic(highs, lows, closes)
        assert all(0 <= v <= 100 for v in k), f"K 범위 벗어남: {[v for v in k if not (0 <= v <= 100)]}"
        assert all(0 <= v <= 100 for v in d), f"D 범위 벗어남"

    def test_constant_price_returns_50(self) -> None:
        """가격이 변하지 않으면 K=50 (high==low → 강제 50)."""
        n = 30
        highs = [100.0] * n
        lows = [100.0] * n
        closes = [100.0] * n
        k, d = calc_stochastic(highs, lows, closes)
        assert all(abs(v - 50.0) < 1e-4 for v in k)

    def test_insufficient_data_returns_empty(self) -> None:
        highs = [110.0] * 5
        lows = [90.0] * 5
        closes = [100.0] * 5
        k, d = calc_stochastic(highs, lows, closes)
        assert k == [] and d == []
