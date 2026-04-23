"""
워치리스트 확장 엔드포인트 — Sprint-08 B-2.

GET /watchlist/summary
GET /watchlist/popular
GET /watchlist/gainers-losers

기존 /market/watchlist/items CRUD 는 market.py 유지 (breaking change 방지).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api import market as market_module
from app.schemas.watchlist import TopListItem, WatchlistSummary
from app.services.watchlist import (
    compute_summary,
    generate_gainers_losers_stub,
    generate_popular_stub,
    sparkline_7d,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/summary", response_model=WatchlistSummary)
async def get_watchlist_summary() -> WatchlistSummary:  # noqa: ANN201
    """현재 워치리스트 기반 통계 요약.

    demo user(_watchlist in-memory) 기준으로 집계.
    워치리스트가 비어 있으면 전부 0 반환.
    """
    raw_items: list[dict[str, Any]] = [dict(item) for item in market_module._watchlist.values()]  # noqa: E501

    # stub 가격 데이터 주입 (market 아이템은 code/market 만 갖고 있음)
    enriched: list[dict[str, Any]] = []
    for item in raw_items:
        pnl = sparkline_7d(str(item.get("market") or ""), str(item.get("code") or ""))
        # 마지막 값 기준 change 계산 (7일 중 첫값 대비 마지막값)
        if len(pnl) >= 2:
            change_raw = (pnl[-1] - pnl[0]) / pnl[0] * 100
            change_pct_str = f"+{change_raw:.2f}" if change_raw >= 0 else f"{change_raw:.2f}"
        else:
            change_pct_str = "+0.00"
        enriched.append({
            "name": item.get("code", "Unknown"),  # memo 없으면 code 를 name 으로
            "change_pct": change_pct_str,
        })

    return compute_summary(enriched)


@router.get("/popular", response_model=list[TopListItem])
async def get_popular() -> list[TopListItem]:
    """전역 인기 종목 Top-5 (stub 하드코드 — AAPL/NVDA/005930/KRW-BTC/TSLA)."""
    return generate_popular_stub()


@router.get("/gainers-losers")
async def get_gainers_losers() -> dict[str, list[TopListItem]]:
    """상승/하락 Top-5 (stub 하드코드, deterministic).

    응답: `{"gainers": [...], "losers": [...]}`
    """
    return generate_gainers_losers_stub()
