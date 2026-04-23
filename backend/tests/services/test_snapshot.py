"""포트폴리오 스냅샷 서비스 단위 테스트."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _insert_holding(
    session: AsyncSession,
    market: str = "upbit",
    code: str = "KRW-BTC",
    quantity: str = "1.0",
    avg_cost: str = "50000000",
    currency: str = "KRW",
) -> Any:
    """테스트용 holding 직접 INSERT."""
    from sqlalchemy import insert as sa_insert

    from app.db.models import Holding

    now = datetime.now(UTC)
    return sa_insert(Holding).values(
        user_id="demo",
        market=market,
        code=code,
        quantity=Decimal(quantity),
        avg_cost=Decimal(avg_cost),
        currency=currency,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_take_snapshot_empty_holdings(db_session: AsyncSession) -> None:
    """빈 holdings → 스냅샷 생성 (값 모두 0)."""
    from app.services.portfolio_snapshot import take_snapshot

    # compute_summary mock — DB I/O 없이
    with patch("app.services.portfolio_snapshot.compute_summary") as mock_cs:
        from app.schemas.portfolio import PortfolioSummary

        mock_cs.return_value = PortfolioSummary(
            user_id="demo",
            total_value_krw="0.00",
            total_cost_krw="0.00",
            total_pnl_krw="0.00",
            total_pnl_pct="0.00",
            daily_change_krw="0.00",
            daily_change_pct="0.00",
            asset_class_breakdown={},
            holdings=[],
        )

        snap = await take_snapshot(db_session, user_id="demo")

    assert snap.snapshot_date == date.today()
    assert snap.total_value_krw == Decimal("0.00")
    assert snap.total_pnl_krw == Decimal("0.00")
    assert snap.user_id == "demo"


@pytest.mark.asyncio
async def test_take_snapshot_with_holdings(db_session: AsyncSession) -> None:
    """holdings 있을 때 스냅샷 값 반영."""
    from app.services.portfolio_snapshot import take_snapshot

    # holding 삽입
    await db_session.execute(_insert_holding(db_session))
    await db_session.commit()

    with patch("app.services.portfolio_snapshot.compute_summary") as mock_cs:
        from app.schemas.portfolio import PortfolioSummary

        mock_cs.return_value = PortfolioSummary(
            user_id="demo",
            total_value_krw="60000000.00",
            total_cost_krw="50000000.00",
            total_pnl_krw="10000000.00",
            total_pnl_pct="20.00",
            daily_change_krw="0.00",
            daily_change_pct="0.00",
            asset_class_breakdown={"crypto": "1.0000"},
            holdings=[],
        )

        snap = await take_snapshot(db_session, user_id="demo")

    assert snap.total_value_krw == Decimal("60000000.00")
    assert snap.total_pnl_krw == Decimal("10000000.00")
    assert snap.asset_class_breakdown == {"crypto": "1.0000"}


@pytest.mark.asyncio
async def test_take_snapshot_upsert_same_date(db_session: AsyncSession) -> None:
    """같은 날 두 번 take_snapshot → upsert (id 동일 or 갱신)."""
    from app.schemas.portfolio import PortfolioSummary
    from app.services.portfolio_snapshot import take_snapshot

    def make_summary(val: str) -> PortfolioSummary:
        return PortfolioSummary(
            user_id="demo",
            total_value_krw=val,
            total_cost_krw="0.00",
            total_pnl_krw="0.00",
            total_pnl_pct="0.00",
            daily_change_krw="0.00",
            daily_change_pct="0.00",
            asset_class_breakdown={},
            holdings=[],
        )

    with patch("app.services.portfolio_snapshot.compute_summary", return_value=make_summary("1000000.00")):
        snap1 = await take_snapshot(db_session, user_id="demo")

    with patch("app.services.portfolio_snapshot.compute_summary", return_value=make_summary("2000000.00")):
        snap2 = await take_snapshot(db_session, user_id="demo")

    # 같은 날짜 스냅샷이 갱신됨 — 최신 값 확인
    assert snap2.total_value_krw == Decimal("2000000.00")
    # snapshot_date 는 오늘로 동일
    assert snap1.snapshot_date == snap2.snapshot_date


@pytest.mark.asyncio
async def test_seed_dummy_snapshots_inserts_7_records(db_session: AsyncSession) -> None:
    """seed_dummy_snapshots → 최대 7개 더미 스냅샷 삽입."""
    from app.db.models import PortfolioSnapshot
    from app.services.portfolio_snapshot import seed_dummy_snapshots

    inserted = await seed_dummy_snapshots(db_session, user_id="demo", days=7)

    # 7개 이하 삽입 (이미 존재하면 스킵)
    assert len(inserted) <= 7
    assert len(inserted) > 0

    result = await db_session.execute(
        select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == "demo")
    )
    all_snaps = result.scalars().all()
    assert len(all_snaps) == len(inserted)


@pytest.mark.asyncio
async def test_seed_dummy_snapshots_no_duplicate(db_session: AsyncSession) -> None:
    """seed_dummy_snapshots 두 번 호출 → 중복 없음."""
    from app.db.models import PortfolioSnapshot
    from app.services.portfolio_snapshot import seed_dummy_snapshots

    await seed_dummy_snapshots(db_session, user_id="demo", days=3)
    # 두 번 호출해도 중복 없음
    await seed_dummy_snapshots(db_session, user_id="demo", days=3)

    result = await db_session.execute(
        select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == "demo")
    )
    all_snaps = result.scalars().all()
    # 3개만 존재
    assert len(all_snaps) == 3
