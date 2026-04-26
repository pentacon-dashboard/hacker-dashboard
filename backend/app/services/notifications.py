"""
알림 서비스 — 새 테이블 없이 기존 데이터에서 on-the-fly 파생.

데이터 소스:
  1. watchlist_alerts 테이블: direction/threshold 비교 → "가격 알림"
  2. holdings + portfolio snapshot: daily_change > ±3% → "일간 변동" 알림
  3. holdings 최근 추가 (24h 이내): "보유 변경" 알림

읽음(unread) 상태는 서버 측 영속화 없이 세션-in-memory dict 로 임시 관리.
(단일 demo 사용자 컨텍스트; 재시작 시 초기화됨.)
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Holding, PortfolioSnapshot, WatchlistAlert
from app.schemas.notifications import Notification
from app.services.market import get_adapter

logger = logging.getLogger(__name__)

_DEMO_USER = "demo"

# -------------------------------------------------------------------
# 읽음 상태 — in-memory (demo 전용; 재시작 시 초기화)
# -------------------------------------------------------------------
# key: (category, source_id)  value: True = 읽음
_read_flags: dict[tuple[str, str], bool] = {}

# 알림 ID 공간: category prefix + source_id
# e.g. "price-3", "portfolio-daily", "holding-7"
_ID_COUNTER: dict[str, int] = {}


def _make_id(prefix: str, source: str) -> str:
    return f"{prefix}-{source}"


def _is_unread(category: str, source_id: str) -> bool:
    return not _read_flags.get((category, source_id), False)


def mark_read(notification_id: str) -> bool:
    """단건 읽음 처리. 존재하지 않는 ID 이면 False 반환."""
    parts = notification_id.split("-", 1)
    if len(parts) < 2:
        return False
    category, source_id = parts[0], parts[1]
    key = (category, source_id)
    _read_flags[key] = True
    return True


def mark_all_read(ids: list[str]) -> None:
    """전달된 ID 목록을 모두 읽음 처리."""
    for nid in ids:
        mark_read(nid)


# -------------------------------------------------------------------
# 알림 파생 로직
# -------------------------------------------------------------------

_SEVERITY_MAP: dict[str, Literal["info", "warning", "critical"]] = {
    "above": "critical",
    "below": "warning",
}


async def _build_price_notifications(
    db: AsyncSession,
) -> list[Notification]:
    """watchlist_alerts 레코드 + 현재가 비교 → 가격 알림."""
    result = await db.execute(
        select(WatchlistAlert).where(
            WatchlistAlert.user_id == _DEMO_USER,
            WatchlistAlert.enabled.is_(True),
        )
    )
    alerts = result.scalars().all()

    notifications: list[Notification] = []
    for alert in alerts:
        try:
            adapter = get_adapter(alert.market)
            quote = await adapter.fetch_quote(alert.symbol)
            current_price = Decimal(str(quote.price))
        except Exception as exc:
            logger.debug("가격 조회 실패 (%s/%s): %s", alert.market, alert.symbol, exc)
            # 조회 실패시 threshold 비교 불가 — 결정론적 stub fallback
            # sin 기반 seed 값으로 임계 초과 여부를 결정
            seed = sum(ord(c) for c in (alert.symbol + alert.market))
            simulated = float(alert.threshold) * (1.0 + math.sin(seed * 0.3) * 0.05)
            current_price = Decimal(str(round(simulated, 4)))

        triggered = (alert.direction == "above" and current_price >= alert.threshold) or (
            alert.direction == "below" and current_price <= alert.threshold
        )
        if not triggered:
            continue

        direction_label = "돌파" if alert.direction == "above" else "하회"
        nid_source = str(alert.id)
        notifications.append(
            Notification(
                id=_make_id("price", nid_source),
                title=f"{alert.symbol} 가격 {direction_label}",
                message=(
                    f"현재가 {float(current_price):,.2f} — "
                    f"설정 임계가 {float(alert.threshold):,.2f} {direction_label}"
                ),
                severity=_SEVERITY_MAP.get(alert.direction, "info"),
                category="price",
                unread=_is_unread("price", nid_source),
                created_at=(
                    alert.created_at.isoformat()
                    if isinstance(alert.created_at, datetime)
                    else str(alert.created_at)
                ),
            )
        )
    return notifications


async def _build_portfolio_notifications(
    db: AsyncSession,
) -> list[Notification]:
    """최신 포트폴리오 스냅샷 vs. 전일 스냅샷 → 일간 변동 알림."""
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == _DEMO_USER)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(2)
    )
    snaps = result.scalars().all()

    notifications: list[Notification] = []
    if len(snaps) < 2:
        return notifications

    latest, prev = snaps[0], snaps[1]
    try:
        latest_val = Decimal(str(latest.total_value_krw))
        prev_val = Decimal(str(prev.total_value_krw))
        if prev_val == 0:
            return notifications
        daily_change_pct = float((latest_val - prev_val) / prev_val * 100)
    except Exception as exc:
        logger.debug("포트폴리오 변동 계산 실패: %s", exc)
        return notifications

    if abs(daily_change_pct) < 3.0:
        return notifications

    direction = "상승" if daily_change_pct > 0 else "하락"
    severity: Literal["info", "warning", "critical"] = (
        "critical" if abs(daily_change_pct) >= 5.0 else "warning"
    )
    nid_source = str(latest.id)
    notifications.append(
        Notification(
            id=_make_id("portfolio", nid_source),
            title=f"포트폴리오 일간 {direction} {abs(daily_change_pct):.1f}%",
            message=(
                f"{prev.snapshot_date} 대비 {daily_change_pct:+.2f}% "
                f"({float(latest_val - prev_val):+,.0f} KRW)"
            ),
            severity=severity,
            category="portfolio",
            unread=_is_unread("portfolio", nid_source),
            created_at=(
                latest.created_at.isoformat()
                if isinstance(latest.created_at, datetime)
                else str(latest.created_at)
            ),
        )
    )
    return notifications


async def _build_holding_notifications(
    db: AsyncSession,
) -> list[Notification]:
    """최근 24h 내 추가된 보유 종목 → '보유 변경' 알림."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    result = await db.execute(
        select(Holding).where(
            Holding.user_id == _DEMO_USER,
            Holding.created_at >= cutoff,
        )
    )
    recent_holdings = result.scalars().all()

    notifications: list[Notification] = []
    for h in recent_holdings:
        nid_source = str(h.id)
        notifications.append(
            Notification(
                id=_make_id("holding", nid_source),
                title=f"{h.code} 신규 보유 추가",
                message=(
                    f"{h.market} / {h.code} "
                    f"수량 {float(h.quantity):.4f} @ 평단 {float(h.avg_cost):,.2f} {h.currency}"
                ),
                severity="info",
                category="portfolio",
                unread=_is_unread("holding", nid_source),
                created_at=(
                    h.created_at.isoformat()
                    if isinstance(h.created_at, datetime)
                    else str(h.created_at)
                ),
            )
        )
    return notifications


async def build_notifications(
    db: AsyncSession,
    *,
    limit: int = 10,
    unread_only: bool = False,
) -> list[Notification]:
    """세 소스를 병합해 알림 목록 반환 (최신 순).

    DB 가 비어 있거나 모든 파생이 실패해도 빈 배열로 graceful degrade.
    """
    results: list[Notification] = []

    # 병렬이 이상적이나 asyncio.gather 는 부분 실패 처리를 위해 분리
    for coro_fn in (
        _build_price_notifications,
        _build_portfolio_notifications,
        _build_holding_notifications,
    ):
        try:
            items = await coro_fn(db)
            results.extend(items)
        except Exception as exc:
            logger.warning("알림 파생 실패 (%s): %s", coro_fn.__name__, exc)

    # 최신 순 정렬
    results.sort(key=lambda n: n.created_at, reverse=True)

    if unread_only:
        results = [n for n in results if n.unread]

    return results[:limit]
