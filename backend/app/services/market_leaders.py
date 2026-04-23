"""시장 주도주 stub 서비스 — Sprint-08 Phase 2-A.

실 시장 데이터 연동은 non-goal. 결정론적 stub 리스트를 반환.
"""
from __future__ import annotations

from app.schemas.portfolio import MarketLeader

_STUB_LEADERS: list[dict[str, str | int]] = [
    {
        "rank": 1,
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "market": "yahoo",
        "price": "847.23",
        "change_pct": "+3.87",
        "currency": "USD",
    },
    {
        "rank": 2,
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "market": "yahoo",
        "price": "273.43",
        "change_pct": "+2.73",
        "currency": "USD",
    },
    {
        "rank": 3,
        "ticker": "TSLA",
        "name": "Tesla Inc.",
        "market": "yahoo",
        "price": "215.80",
        "change_pct": "-1.72",
        "currency": "USD",
    },
    {
        "rank": 4,
        "ticker": "005930",
        "name": "삼성전자",
        "market": "naver_kr",
        "price": "72000",
        "change_pct": "+0.56",
        "currency": "KRW",
    },
    {
        "rank": 5,
        "ticker": "KRW-BTC",
        "name": "Bitcoin",
        "market": "upbit",
        "price": "115898000",
        "change_pct": "+2.11",
        "currency": "KRW",
    },
]


def get_market_leaders(limit: int = 5) -> list[MarketLeader]:
    """stub 시장 주도주 목록 반환.

    limit 개까지 잘라서 반환. rank 는 1부터 순서대로.
    """
    items = _STUB_LEADERS[:limit]
    result: list[MarketLeader] = []
    for i, row in enumerate(items, start=1):
        result.append(
            MarketLeader(
                rank=i,
                ticker=row["ticker"],
                name=row["name"],
                market=row["market"],
                price=row["price"],
                change_pct=row["change_pct"],
                currency=row["currency"],
            )
        )
    return result
