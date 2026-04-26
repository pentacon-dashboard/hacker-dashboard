"""
워치리스트 확장 엔드포인트 — Sprint-08 B-2 + Phase 2-D (알림 CRUD).

GET  /watchlist/summary
GET  /watchlist/popular
GET  /watchlist/gainers-losers
GET  /watchlist/alerts
POST /watchlist/alerts
PATCH /watchlist/alerts/{id}
DELETE /watchlist/alerts/{id}

기존 /market/watchlist/items CRUD 는 market.py 유지 (breaking change 방지).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import market as market_module
from app.db.models import WatchlistAlert
from app.db.session import get_db
from app.schemas.watchlist import (
    TopListItem,
    WatchlistAlertCreate,
    WatchlistAlertResponse,
    WatchlistAlertUpdate,
    WatchlistSummary,
)
from app.services.watchlist import (
    compute_summary,
    generate_gainers_losers_stub,
    generate_popular_stub,
    sparkline_7d,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

_DEMO_USER = "demo"


def _alert_to_response(a: WatchlistAlert) -> WatchlistAlertResponse:
    return WatchlistAlertResponse(
        id=a.id,
        user_id=a.user_id,
        symbol=a.symbol,
        market=a.market,
        direction=a.direction,
        threshold=str(a.threshold),
        enabled=a.enabled,
        created_at=a.created_at.isoformat()
        if isinstance(a.created_at, datetime)
        else str(a.created_at),
    )


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
        enriched.append(
            {
                "name": item.get("code", "Unknown"),  # memo 없으면 code 를 name 으로
                "change_pct": change_pct_str,
            }
        )

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


# ── Phase 2-D: 알림 CRUD ─────────────────────────────────────────────────────


@router.get(
    "/alerts",
    response_model=list[WatchlistAlertResponse],
    summary="워치리스트 알림 목록 조회",
)
async def list_watchlist_alerts(
    db: AsyncSession = Depends(get_db),
) -> list[WatchlistAlertResponse]:
    """demo user 의 워치리스트 알림 전체 조회."""
    result = await db.execute(
        select(WatchlistAlert)
        .where(WatchlistAlert.user_id == _DEMO_USER)
        .order_by(WatchlistAlert.id)
    )
    alerts = result.scalars().all()
    return [_alert_to_response(a) for a in alerts]


@router.post(
    "/alerts",
    response_model=WatchlistAlertResponse,
    status_code=201,
    summary="워치리스트 알림 추가",
    responses={400: {"description": "JSON 파싱 실패"}},
)
async def create_watchlist_alert(
    body: WatchlistAlertCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchlistAlertResponse:
    """워치리스트 알림 신규 생성."""
    now = datetime.now(UTC)
    alert = WatchlistAlert(
        user_id=_DEMO_USER,
        symbol=body.symbol,
        market=body.market,
        direction=body.direction,
        threshold=body.threshold,
        enabled=True,
        created_at=now,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_to_response(alert)


@router.patch(
    "/alerts/{alert_id}",
    response_model=WatchlistAlertResponse,
    summary="워치리스트 알림 수정",
    responses={404: {"description": "알림을 찾을 수 없음"}},
)
async def update_watchlist_alert(
    body: WatchlistAlertUpdate,
    alert_id: int = Path(..., ge=1, description="알림 ID"),
    db: AsyncSession = Depends(get_db),
) -> WatchlistAlertResponse:
    """알림 활성화 여부 또는 임계가격 변경."""
    result = await db.execute(
        select(WatchlistAlert).where(
            WatchlistAlert.id == alert_id,
            WatchlistAlert.user_id == _DEMO_USER,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"alert {alert_id} not found")

    if body.enabled is not None:
        alert.enabled = body.enabled
    if body.threshold is not None:
        alert.threshold = body.threshold

    await db.commit()
    await db.refresh(alert)
    return _alert_to_response(alert)


@router.delete(
    "/alerts/{alert_id}",
    status_code=204,
    summary="워치리스트 알림 삭제",
    responses={404: {"description": "알림을 찾을 수 없음"}},
)
async def delete_watchlist_alert(
    alert_id: int = Path(..., ge=1, description="알림 ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """워치리스트 알림 삭제."""
    result = await db.execute(
        select(WatchlistAlert).where(
            WatchlistAlert.id == alert_id,
            WatchlistAlert.user_id == _DEMO_USER,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"alert {alert_id} not found")

    await db.delete(alert)
    await db.commit()
