"""
기술 지표 계산 서비스 — Sprint-08 B-3.

순수 numpy 구현 (외부 ta 라이브러리 없이).
calc_rsi, calc_macd, calc_bollinger, calc_stochastic
"""
from __future__ import annotations

import numpy as np


def calc_rsi(closes: list[float], period: int = 14) -> list[float]:
    """Wilder's RSI.

    반환 길이: len(closes) - period  (period 이전 값은 NaN 이므로 제거)
    최소 len(closes) > period 이어야 한다.
    """
    if len(closes) <= period:
        return []

    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # 첫 번째 평균 (단순)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    rsi_values: list[float] = []

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi_values.append(round(rsi, 4))

    return rsi_values


def calc_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """MACD 계산.

    반환: (macd_line, signal_line, histogram)
    모두 동일 길이. slow-1 이전은 NaN 이므로 slow-1 부터 시작.
    """
    if len(closes) < slow + signal:
        return [], [], []

    arr = np.array(closes, dtype=float)

    def _ema(data: np.ndarray, span: int) -> np.ndarray:
        alpha = 2.0 / (span + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    ema_fast = _ema(arr, fast)
    ema_slow = _ema(arr, slow)

    macd_line = ema_fast - ema_slow
    # signal 은 macd_line 의 EMA
    signal_line = _ema(macd_line[slow - 1:], signal)
    histogram = macd_line[slow - 1:] - signal_line

    # 길이 맞춤: slow-1 이후 데이터
    macd_out = macd_line[slow - 1:].tolist()
    signal_out = signal_line.tolist()
    hist_out = histogram.tolist()

    # 반올림
    macd_out = [round(v, 6) for v in macd_out]
    signal_out = [round(v, 6) for v in signal_out]
    hist_out = [round(v, 6) for v in hist_out]

    return macd_out, signal_out, hist_out


def calc_bollinger(
    closes: list[float],
    period: int = 20,
    k: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    """볼린저 밴드 계산.

    반환: (upper, mid, lower) — 각 길이 len(closes) - period + 1
    """
    if len(closes) < period:
        return [], [], []

    arr = np.array(closes, dtype=float)
    uppers: list[float] = []
    mids: list[float] = []
    lowers: list[float] = []

    for i in range(period - 1, len(arr)):
        window = arr[i - period + 1: i + 1]
        mid = float(np.mean(window))
        std = float(np.std(window, ddof=0))
        uppers.append(round(mid + k * std, 4))
        mids.append(round(mid, 4))
        lowers.append(round(mid - k * std, 4))

    return uppers, mids, lowers


def calc_ma(prices: list[float], period: int) -> list[float]:
    """단순 이동평균(SMA) 계산.

    반환 길이: len(prices) - period + 1
    period 미만 길이 입력 시 빈 리스트 반환.
    """
    if len(prices) < period:
        return []

    arr = np.array(prices, dtype=float)
    result: list[float] = []
    for i in range(period - 1, len(arr)):
        window = arr[i - period + 1 : i + 1]
        result.append(round(float(np.mean(window)), 4))
    return result


def calc_stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
) -> tuple[list[float], list[float]]:
    """스토캐스틱 %K, %D 계산.

    반환: (K, D) — 동일 길이
    """
    if len(closes) < period + smooth_k + smooth_d:
        return [], []

    h = np.array(highs, dtype=float)
    lo = np.array(lows, dtype=float)
    c = np.array(closes, dtype=float)

    raw_k: list[float] = []
    for i in range(period - 1, len(c)):
        window_h = h[i - period + 1: i + 1]
        window_lo = lo[i - period + 1: i + 1]
        hh = float(np.max(window_h))
        ll = float(np.min(window_lo))
        if hh == ll:
            raw_k.append(50.0)
        else:
            raw_k.append(round((c[i] - ll) / (hh - ll) * 100, 4))

    # %K smoothing (rolling mean of raw_k)
    def _rolling_mean(data: list[float], w: int) -> list[float]:
        arr = np.array(data, dtype=float)
        result = []
        for i in range(w - 1, len(arr)):
            result.append(round(float(np.mean(arr[i - w + 1: i + 1])), 4))
        return result

    smooth_k_vals = _rolling_mean(raw_k, smooth_k)
    smooth_d_vals = _rolling_mean(smooth_k_vals, smooth_d)

    # 길이를 %D 기준으로 맞춤
    offset = len(smooth_k_vals) - len(smooth_d_vals)
    k_out = smooth_k_vals[offset:]

    return k_out, smooth_d_vals
