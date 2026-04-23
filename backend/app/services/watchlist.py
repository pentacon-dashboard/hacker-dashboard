"""
워치리스트 도메인 서비스 — Sprint-08 B-2.

compute_summary, generate_popular_stub, generate_gainers_losers_stub, sparkline_7d
"""
from __future__ import annotations

import math
from typing import Any

from app.schemas.watchlist import TopListItem, WatchlistSummary

# ──────────────── 스파크라인 ────────────────

def sparkline_7d(market: str, code: str) -> list[float]:
    """7일 종가 스파크라인 — deterministic sin-based stub.

    market + code 를 시드로 삼아 동일 입력이면 항상 같은 패턴을 반환한다.
    """
    seed = sum(ord(c) for c in (market + code))
    base = 100.0 + (seed % 200)  # 100~300 범위 기준가
    result: list[float] = []
    for i in range(7):
        # sin 파형 + 작은 노이즈 (seed 로 고정)
        offset = math.sin(i * 0.8 + seed * 0.1) * base * 0.03
        noise = ((seed * (i + 7)) % 17 - 8) * base * 0.002
        result.append(round(base + offset + noise, 2))
    return result


# ──────────────── 통계 계산 ────────────────

def _parse_change_pct(change_pct: str) -> float:
    """'+3.21' / '-1.50' → float."""
    try:
        return float(change_pct.replace("+", "").replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def compute_summary(items: list[dict[str, Any]]) -> WatchlistSummary:
    """워치리스트 아이템 목록으로 요약 통계 계산.

    items 는 WatchlistItem-compatible dict (change_pct, name 필드 필요).
    """
    if not items:
        return WatchlistSummary(
            watched_count=0,
            up_avg_pct="+0.00",
            down_avg_pct="-0.00",
            top_gainer_name="-",
            top_gainer_pct="+0.00",
        )

    up_pcts: list[float] = []
    down_pcts: list[float] = []
    best_pct: float = float("-inf")
    best_name: str = "-"

    for item in items:
        pct = _parse_change_pct(str(item.get("change_pct", "0")))
        name = str(item.get("name", "Unknown"))
        if pct >= 0:
            up_pcts.append(pct)
        else:
            down_pcts.append(pct)
        if pct > best_pct:
            best_pct = pct
            best_name = name

    up_avg = sum(up_pcts) / len(up_pcts) if up_pcts else 0.0
    down_avg = sum(down_pcts) / len(down_pcts) if down_pcts else 0.0

    def _fmt_pct(v: float, positive: bool) -> str:
        sign = "+" if positive else ""
        return f"{sign}{v:.2f}"

    top_gainer_pct = _fmt_pct(best_pct, best_pct >= 0) if best_pct != float("-inf") else "+0.00"

    return WatchlistSummary(
        watched_count=len(items),
        up_avg_pct=_fmt_pct(up_avg, True),
        down_avg_pct=f"-{abs(down_avg):.2f}",
        top_gainer_name=best_name,
        top_gainer_pct=top_gainer_pct,
    )


# ──────────────── Stub 생성기 ────────────────

_POPULAR_STUBS: list[dict[str, Any]] = [
    {"rank": 1, "ticker": "AAPL", "name": "Apple Inc.", "change_pct": "+1.23", "views_24h": 94821},
    {"rank": 2, "ticker": "NVDA", "name": "NVIDIA", "change_pct": "+3.87", "views_24h": 87432},
    {"rank": 3, "ticker": "005930", "name": "삼성전자", "change_pct": "-0.54", "views_24h": 65341},
    {"rank": 4, "ticker": "KRW-BTC", "name": "Bitcoin/KRW", "change_pct": "+2.11", "views_24h": 58920},
    {"rank": 5, "ticker": "TSLA", "name": "Tesla", "change_pct": "-1.72", "views_24h": 51234},
]

_GAINERS_STUBS: list[dict[str, Any]] = [
    {"rank": 1, "ticker": "NVDA", "name": "NVIDIA", "change_pct": "+3.87"},
    {"rank": 2, "ticker": "005930", "name": "삼성전자", "change_pct": "+3.21"},
    {"rank": 3, "ticker": "KRW-BTC", "name": "Bitcoin/KRW", "change_pct": "+2.11"},
    {"rank": 4, "ticker": "AAPL", "name": "Apple Inc.", "change_pct": "+1.23"},
    {"rank": 5, "ticker": "MSFT", "name": "Microsoft", "change_pct": "+0.89"},
]

_LOSERS_STUBS: list[dict[str, Any]] = [
    {"rank": 1, "ticker": "TSLA", "name": "Tesla", "change_pct": "-1.72"},
    {"rank": 2, "ticker": "META", "name": "Meta Platforms", "change_pct": "-1.44"},
    {"rank": 3, "ticker": "GOOGL", "name": "Alphabet", "change_pct": "-1.09"},
    {"rank": 4, "ticker": "AMZN", "name": "Amazon", "change_pct": "-0.83"},
    {"rank": 5, "ticker": "KRW-ETH", "name": "Ethereum/KRW", "change_pct": "-0.61"},
]


def generate_popular_stub() -> list[TopListItem]:
    """전역 인기 종목 Top-5 stub."""
    return [TopListItem(**row) for row in _POPULAR_STUBS]


def generate_gainers_losers_stub() -> dict[str, list[TopListItem]]:
    """상승/하락 Top-5 stub (deterministic)."""
    return {
        "gainers": [TopListItem(**row) for row in _GAINERS_STUBS],
        "losers": [TopListItem(**row) for row in _LOSERS_STUBS],
    }
