"""
알림 엔드포인트.

GET  /notifications           — 알림 목록 (limit, unread_only 쿼리 파라미터)
POST /notifications/{id}/read — 단건 읽음 처리
POST /notifications/read-all  — 전체 읽음 처리

데이터는 watchlist_alerts + holdings + portfolio_snapshots 에서 on-the-fly 파생.
새 DB 테이블 없음 (옵션 A).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.notifications import (
    MarkAllReadResponse,
    MarkReadResponse,
    Notification,
)
from app.services.notifications import (
    build_notifications,
    mark_all_read,
    mark_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[Notification],
    summary="알림 목록 조회",
    description=(
        "watchlist_alerts + holdings + portfolio_snapshots 에서 파생한 알림 목록. "
        "새 테이블 없이 on-the-fly 계산."
    ),
)
async def list_notifications(
    limit: int = Query(10, ge=1, le=50, description="반환 개수 (1~50)"),
    unread_only: bool = Query(False, description="미확인 알림만 반환"),
    db: AsyncSession = Depends(get_db),
) -> list[Notification]:
    """알림 목록 반환."""
    return await build_notifications(db, limit=limit, unread_only=unread_only)


# NOTE: read-all 라우트를 {id}/read 보다 먼저 등록해야 FastAPI 가 올바르게 매칭한다.
@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="전체 읽음 처리",
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    """현재 알림 목록 전체를 읽음 처리한다."""
    items = await build_notifications(db, limit=50, unread_only=False)
    ids = [n.id for n in items]
    mark_all_read(ids)
    return MarkAllReadResponse(marked_count=len(ids))


@router.post(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="단건 읽음 처리",
    responses={404: {"description": "알림을 찾을 수 없음"}},
)
async def mark_notification_read(
    notification_id: str = Path(
        ...,
        description="알림 ID (예: price-3, portfolio-12)",
        pattern=r"^[a-z]+-\S+$",
    ),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """단일 알림을 읽음 처리한다."""
    # 먼저 해당 알림이 현재 목록에 존재하는지 확인
    items = await build_notifications(db, limit=50, unread_only=False)
    existing_ids = {n.id for n in items}

    # 존재하지 않아도 mark_read 는 허용 (idempotent) — 단 404 응답은 하지 않음
    # (POST /notifications/{id}/read 수락 기준: 200 반환이면 충분)
    success = mark_read(notification_id)
    if not success and notification_id not in existing_ids:
        raise HTTPException(
            status_code=404, detail=f"notification {notification_id!r} not found"
        )
    # mark_read 가 False 를 반환해도 ID 가 목록에 있으면 처리
    mark_read(notification_id)

    return MarkReadResponse(id=notification_id, unread=False)
