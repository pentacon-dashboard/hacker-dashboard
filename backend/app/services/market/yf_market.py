"""yfinance 기반 시장 지수 / 섹터 / 원자재 실시간 데이터 서비스.

모든 yfinance 호출은 executor (스레드풀) 에서 동기 실행 후 비동기로 래핑.
캐시 TTL: 60초 (yf_cache.py in-memory).
실패 시 market_fixtures.py stub 폴백.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.market.yf_cache import yf_cache_get, yf_cache_set

logger = logging.getLogger(__name__)

# ─── 인덱스 티커 정의 ──────────────────────────────────────────────────────────

_INDEX_TICKERS: dict[str, str] = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW Jones": "^DJI",
    "VIX (공포 지수)": "^VIX",
    "USD/KRW": "KRW=X",
}

# ─── 섹터 ETF 정의 ────────────────────────────────────────────────────────────

_SECTOR_ETF: dict[str, str] = {
    "정보기술": "XLK",
    "반도체": "SOXX",
    "헬스케어": "XLV",
    "금융": "XLF",
    "임의소비재": "XLY",
    "필수소비재": "XLP",
    "에너지": "XLE",
    "소재": "XLB",
    "산업재": "XLI",
    "통신서비스": "XLC",
    "유틸리티": "XLU",
}

# ─── 원자재 심볼 정의 ─────────────────────────────────────────────────────────

_COMMODITY_INFO: dict[str, dict[str, str]] = {
    "GC=F": {"name": "금", "unit": "USD/oz"},
    "SI=F": {"name": "은", "unit": "USD/oz"},
    "CL=F": {"name": "WTI 원유", "unit": "USD/bbl"},
    "BZ=F": {"name": "브렌트유", "unit": "USD/bbl"},
    "NG=F": {"name": "천연가스", "unit": "USD/MMBtu"},
}


# ─── 동기 헬퍼 (executor 에서 실행) ──────────────────────────────────────────


def _fetch_indices_sync() -> list[dict[str, Any]] | None:
    """yfinance 로 7개 인덱스 스냅샷 조회."""
    import yfinance as yf

    symbols = list(_INDEX_TICKERS.values())
    names = list(_INDEX_TICKERS.keys())
    results: list[dict[str, Any]] = []

    for display_name, ticker_symbol in zip(names, symbols):
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="8d", interval="1d")
            if hist is None or hist.empty:
                return None

            closes = hist["Close"].dropna().tolist()
            if not closes:
                return None

            current = closes[-1]
            prev = closes[-2] if len(closes) >= 2 else current
            change = current - prev
            change_pct = (change / prev * 100.0) if prev else 0.0

            # 스파크라인: 최근 7포인트
            sparkline = [round(float(v), 4) for v in closes[-7:]]
            # 7포인트 미만이면 앞을 첫 값으로 채움
            while len(sparkline) < 7:
                sparkline.insert(0, sparkline[0] if sparkline else 0.0)

            results.append(
                {
                    "ticker": ticker_symbol,
                    "display_name": display_name,
                    "value": _fmt_number(current),
                    "change_pct": _fmt_pct(change_pct),
                    "change_abs": _fmt_abs(change),
                    "sparkline_7d": sparkline,
                }
            )
        except Exception as exc:
            logger.warning("yfinance index 실패 (%s): %s", ticker_symbol, exc)
            return None

    return results if len(results) == len(names) else None


def _fetch_sectors_sync() -> list[dict[str, Any]] | None:
    """SPDR ETF 로 11개 섹터 KPI 조회."""
    import yfinance as yf

    results: list[dict[str, Any]] = []
    for sector_name, etf_symbol in _SECTOR_ETF.items():
        try:
            ticker = yf.Ticker(etf_symbol)
            hist = ticker.history(period="2d", interval="1d")
            if hist is None or hist.empty:
                return None

            closes = hist["Close"].dropna().tolist()
            if len(closes) < 2:
                # 데이터 부족 — 전일 대비 0으로 처리
                change_pct = 0.0
            else:
                change_pct = (closes[-1] - closes[-2]) / closes[-2] * 100.0 if closes[-2] else 0.0

            results.append(
                {
                    "name": sector_name,
                    "change_pct": _fmt_pct(change_pct),
                    "constituents": _SECTOR_CONSTITUENTS.get(sector_name, 30),
                    "leaders": [],  # ETF holdings API 복잡 — 빈 배열
                }
            )
        except Exception as exc:
            logger.warning("yfinance sector 실패 (%s/%s): %s", sector_name, etf_symbol, exc)
            return None

    return results if len(results) == len(_SECTOR_ETF) else None


def _fetch_commodities_sync() -> list[dict[str, Any]] | None:
    """5개 원자재 실시간 시세 조회."""
    import yfinance as yf

    results: list[dict[str, Any]] = []
    for symbol, meta in _COMMODITY_INFO.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", interval="1d")
            if hist is None or hist.empty:
                return None

            closes = hist["Close"].dropna().tolist()
            if not closes:
                return None

            current = closes[-1]
            prev = closes[-2] if len(closes) >= 2 else current
            change_pct = (current - prev) / prev * 100.0 if prev else 0.0

            results.append(
                {
                    "symbol": symbol,
                    "name": meta["name"],
                    "price": _fmt_number(current),
                    "change_pct": _fmt_pct(change_pct),
                    "unit": meta["unit"],
                }
            )
        except Exception as exc:
            logger.warning("yfinance commodity 실패 (%s): %s", symbol, exc)
            return None

    return results if len(results) == len(_COMMODITY_INFO) else None


# ─── 비동기 퍼블릭 API ────────────────────────────────────────────────────────


async def get_indices() -> list[dict[str, Any]] | None:
    """시장 지수 7개. 캐시 히트 시 즉시 반환, miss 시 yfinance 조회."""
    key = "yf:market:indices"
    cached: list[dict[str, Any]] | None = await yf_cache_get(key)
    if cached is not None:
        return cached

    data = await asyncio.get_event_loop().run_in_executor(None, _fetch_indices_sync)
    if data is not None:
        await yf_cache_set(key, data, ttl=60)
    return data


async def get_sectors() -> list[dict[str, Any]] | None:
    """섹터 KPI 11개. 캐시 TTL 60초."""
    key = "yf:market:sectors"
    cached: list[dict[str, Any]] | None = await yf_cache_get(key)
    if cached is not None:
        return cached

    data = await asyncio.get_event_loop().run_in_executor(None, _fetch_sectors_sync)
    if data is not None:
        await yf_cache_set(key, data, ttl=60)
    return data


async def get_commodities() -> list[dict[str, Any]] | None:
    """원자재 5종. 캐시 TTL 60초."""
    key = "yf:market:commodities"
    cached: list[dict[str, Any]] | None = await yf_cache_get(key)
    if cached is not None:
        return cached

    data = await asyncio.get_event_loop().run_in_executor(None, _fetch_commodities_sync)
    if data is not None:
        await yf_cache_set(key, data, ttl=60)
    return data


# ─── 포맷 헬퍼 ───────────────────────────────────────────────────────────────


def _fmt_number(v: float) -> str:
    """숫자를 콤마 포함 문자열로 포맷 (소수점 2자리)."""
    if v >= 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}" if v < 10 else f"{v:.2f}"


def _fmt_pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}"


def _fmt_abs(v: float) -> str:
    sign = "+" if v >= 0 else ""
    if abs(v) >= 1000:
        return f"{sign}{v:,.2f}"
    return f"{sign}{v:.2f}"


# ─── 섹터별 구성 종목 수 근사값 ───────────────────────────────────────────────

_SECTOR_CONSTITUENTS: dict[str, int] = {
    "정보기술": 75,
    "반도체": 30,
    "헬스케어": 60,
    "금융": 65,
    "임의소비재": 50,
    "필수소비재": 38,
    "에너지": 28,
    "소재": 25,
    "산업재": 72,
    "통신서비스": 26,
    "유틸리티": 28,
}
