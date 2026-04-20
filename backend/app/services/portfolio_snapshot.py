"""포트폴리오 스냅샷 서비스 — week-3.

CLI: python -m app.services.portfolio_snapshot
  → 오늘 날짜 스냅샷 upsert

데모용 더미 스냅샷 삽입 기능도 포함.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Holding, PortfolioSnapshot
from app.services.portfolio import _d, _fmt, _classify_asset, compute_summary

logger = logging.getLogger(__name__)


async def take_snapshot(
    session: AsyncSession,
    user_id: str = "demo",
) -> PortfolioSnapshot:
    """현재 holdings 기반으로 오늘 날짜 스냅샷 생성/갱신 (upsert)."""
    today = date.today()

    # holdings 조회
    result = await session.execute(
        select(Holding).where(Holding.user_id == user_id)
    )
    holdings = result.scalars().all()

    # 집계 — 현재가 조회 포함
    summary = await compute_summary(list(holdings))

    breakdown_raw = {k: str(v) for k, v in summary.asset_class_breakdown.items()}
    holdings_detail_raw = [h.model_dump() for h in summary.holdings]

    value_krw = Decimal(summary.total_value_krw)
    pnl_krw = Decimal(summary.total_pnl_krw)

    # 기존 스냅샷 조회 후 INSERT or UPDATE (SQLite/PostgreSQL 모두 호환)
    existing_result = await session.execute(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.snapshot_date == today,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        existing.total_value_krw = value_krw
        existing.total_pnl_krw = pnl_krw
        existing.asset_class_breakdown = breakdown_raw
        existing.holdings_detail = holdings_detail_raw
        snapshot = existing
    else:
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            snapshot_date=today,
            total_value_krw=value_krw,
            total_pnl_krw=pnl_krw,
            asset_class_breakdown=breakdown_raw,
            holdings_detail=holdings_detail_raw,
        )
        session.add(snapshot)

    await session.commit()
    await session.refresh(snapshot)
    logger.info("스냅샷 upsert 완료: user=%s date=%s value_krw=%s", user_id, today, summary.total_value_krw)
    return snapshot


async def seed_dummy_snapshots(
    session: AsyncSession,
    user_id: str = "demo",
    days: int = 7,
) -> list[PortfolioSnapshot]:
    """지난 `days`일 더미 스냅샷 삽입 (그래프가 비어보이지 않게).

    이미 존재하는 날짜는 건너뛴다.
    """
    today = date.today()
    inserted: list[PortfolioSnapshot] = []

    # 기본값 변동폭 (데모용 랜덤하게 보이게)
    base_value = Decimal("5000000")  # 500만원
    base_pnl = Decimal("-50000")

    for i in range(days, 0, -1):
        target_date = today - timedelta(days=i)

        # 이미 존재하면 스킵
        existing = await session.execute(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date == target_date,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        # 더미 변동값
        day_factor = Decimal(str(1 + (i * 0.01 - days * 0.005)))
        value = (base_value * day_factor).quantize(Decimal("0.01"))
        pnl = (base_pnl + Decimal(str(i * 5000))).quantize(Decimal("0.01"))

        snap = PortfolioSnapshot(
            user_id=user_id,
            snapshot_date=target_date,
            total_value_krw=value,
            total_pnl_krw=pnl,
            asset_class_breakdown={"crypto": "0.6000", "stock_us": "0.4000"},
            holdings_detail=[],
        )
        session.add(snap)
        inserted.append(snap)

    await session.commit()
    logger.info("더미 스냅샷 %d건 삽입 완료 (user=%s)", len(inserted), user_id)
    return inserted


async def _main() -> None:
    """CLI 진입점 — 오늘 날짜 스냅샷 upsert."""
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        snap = await take_snapshot(session)
        print(f"Snapshot saved: id={snap.id} date={snap.snapshot_date} value_krw={snap.total_value_krw}")


if __name__ == "__main__":
    asyncio.run(_main())
