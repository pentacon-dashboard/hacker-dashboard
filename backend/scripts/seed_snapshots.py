"""30일치 PortfolioSnapshot 시드 스크립트.

2026-03-25 ~ 2026-04-24 (31일) 범위를 커버한다.
- 30일 전 기준선: 현재 total_value_krw 의 약 95% (5% 성장 trajectory)
- 매일 smooth하게 증가 (sin noise 소량 포함)
- asset_class_breakdown: crypto 0.69 / stock_us 0.22 / stock_kr 0.09
- UPSERT (ON CONFLICT DO UPDATE) → 기존 7개 행과 충돌 없음
"""
from __future__ import annotations

import asyncio
import math
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# backend/ 패키지를 sys.path 에 추가 (스크립트 직접 실행 시)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import PortfolioSnapshot

# ── 시드 파라미터 ────────────────────────────────────────────────────────────

_USER_ID = "demo"
_START_DATE = date(2026, 3, 25)
_END_DATE = date(2026, 4, 24)

# 현재 포트폴리오 총 가치 (summary 기준) — 8,365,502 KRW
_CURRENT_VALUE_KRW = Decimal("8365502.50")

# 30일 전에는 현재의 ~95% 에서 시작해 smooth 하게 증가
_GROWTH_RATIO = 0.95

_ASSET_BREAKDOWN = {
    "crypto": "0.6933",
    "stock_us": "0.2206",
    "stock_kr": "0.0861",
}

# ── 값 생성 ──────────────────────────────────────────────────────────────────


def _generate_values(start: date, end: date) -> list[tuple[date, Decimal, Decimal]]:
    """(snapshot_date, total_value_krw, total_pnl_krw) 목록 생성."""
    days: list[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)

    n = len(days)
    base_start = _CURRENT_VALUE_KRW * Decimal(str(_GROWTH_RATIO))
    base_end = _CURRENT_VALUE_KRW

    rows: list[tuple[date, Decimal, Decimal]] = []
    for i, d in enumerate(days):
        # 선형 기준선
        t = i / max(n - 1, 1)
        linear = base_start + (base_end - base_start) * Decimal(str(t))

        # 작은 sin noise (±0.3%)
        noise_factor = Decimal(str(1 + 0.003 * math.sin(i * 0.7 + 1.2)))
        value = (linear * noise_factor).quantize(Decimal("0.01"))

        # pnl = 현재가 - 원가 기준 (원가는 6,850,000 KRW 고정)
        cost_krw = Decimal("6850000.00")
        pnl = (value - cost_krw).quantize(Decimal("0.01"))

        rows.append((d, value, pnl))

    return rows


# ── DB UPSERT ────────────────────────────────────────────────────────────────


async def seed(session: AsyncSession) -> int:
    """스냅샷 행을 UPSERT 하고 삽입/갱신된 행 수를 반환한다."""
    rows = _generate_values(_START_DATE, _END_DATE)
    upserted = 0

    for snapshot_date, value, pnl in rows:
        # PostgreSQL ON CONFLICT DO UPDATE
        stmt = text(
            """
            INSERT INTO portfolio_snapshots
                (user_id, snapshot_date, total_value_krw, total_pnl_krw,
                 asset_class_breakdown, holdings_detail)
            VALUES
                (:user_id, :snapshot_date, :value, :pnl,
                 CAST(:breakdown AS jsonb), CAST(:detail AS jsonb))
            ON CONFLICT (user_id, snapshot_date)
            DO UPDATE SET
                total_value_krw = EXCLUDED.total_value_krw,
                total_pnl_krw   = EXCLUDED.total_pnl_krw,
                asset_class_breakdown = EXCLUDED.asset_class_breakdown
            """
        )
        import json

        await session.execute(
            stmt,
            {
                "user_id": _USER_ID,
                "snapshot_date": snapshot_date,  # asyncpg needs date object, not str
                "value": str(value),
                "pnl": str(pnl),
                "breakdown": json.dumps(_ASSET_BREAKDOWN),
                "detail": "[]",
            },
        )
        upserted += 1

    await session.commit()
    return upserted


async def main() -> None:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        echo=False,
    )
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async with factory() as session:
        n = await seed(session)

    await engine.dispose()
    print(f"Done: {n} snapshots upserted ({_START_DATE} ~ {_END_DATE})")


if __name__ == "__main__":
    asyncio.run(main())
