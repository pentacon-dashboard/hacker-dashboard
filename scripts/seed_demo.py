"""데모 포트폴리오 시드 스크립트.

사용:
  export DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard"
  uv run python scripts/seed_demo.py

idempotent: 이미 존재하는 (user_id, market, code) 조합이면 건너뜀.

주의: 이 스크립트는 데모 전용입니다. 실거래 데이터가 아닙니다.
"""
from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal

# 프로젝트 루트에서 실행 시 backend 패키지를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Holding

# ── 데모 holdings 정의 ────────────────────────────────────────────────────────
DEMO_HOLDINGS: list[dict] = [
    {
        "user_id": "demo",
        "market": "naver_kr",
        "code": "005930",
        "quantity": Decimal("10"),
        "avg_cost": Decimal("75000"),
        "currency": "KRW",
    },
    {
        "user_id": "demo",
        "market": "yahoo",
        "code": "AAPL",
        "quantity": Decimal("5"),
        "avg_cost": Decimal("185.00"),
        "currency": "USD",
    },
    {
        "user_id": "demo",
        "market": "yahoo",
        "code": "TSLA",
        "quantity": Decimal("3"),
        "avg_cost": Decimal("250.00"),
        "currency": "USD",
    },
    {
        "user_id": "demo",
        "market": "upbit",
        "code": "KRW-BTC",
        "quantity": Decimal("0.05"),
        "avg_cost": Decimal("85000000"),
        "currency": "KRW",
    },
    {
        "user_id": "demo",
        "market": "upbit",
        "code": "KRW-ETH",
        "quantity": Decimal("1.2"),
        "avg_cost": Decimal("4500000"),
        "currency": "KRW",
    },
]


async def seed(session: AsyncSession) -> int:
    """DEMO_HOLDINGS를 DB에 idempotent 삽입. 삽입된 건수를 반환."""
    inserted = 0
    for row in DEMO_HOLDINGS:
        stmt = select(Holding).where(
            Holding.user_id == row["user_id"],
            Holding.market == row["market"],
            Holding.code == row["code"],
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"  SKIP  {row['market']:12s} / {row['code']:10s} — 이미 존재")
            continue

        holding = Holding(**row)
        session.add(holding)
        await session.flush()
        print(
            f"  INSERT {row['market']:12s} / {row['code']:10s}"
            f"  qty={row['quantity']}  avg_cost={row['avg_cost']}  {row['currency']}"
        )
        inserted += 1

    await session.commit()
    return inserted


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        print(
            "  export DATABASE_URL='postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[seed_demo] DB 연결 중: {database_url.split('@')[-1]}")
    try:
        engine = create_async_engine(database_url, pool_pre_ping=True, echo=False)
        session_factory = async_sessionmaker(
            bind=engine, expire_on_commit=False, autoflush=False
        )
    except Exception as exc:
        print(f"ERROR: engine 생성 실패 — {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        async with session_factory() as session:
            print(f"[seed_demo] 데모 holdings {len(DEMO_HOLDINGS)}종 처리 시작...")
            inserted = await seed(session)
    except Exception as exc:
        print(f"ERROR: DB 시드 삽입 실패 — {exc}", file=sys.stderr)
        await engine.dispose()
        sys.exit(1)

    await engine.dispose()

    # 최종 상태 조회
    try:
        engine2 = create_async_engine(database_url, pool_pre_ping=True, echo=False)
        session_factory2 = async_sessionmaker(
            bind=engine2, expire_on_commit=False, autoflush=False
        )
        async with session_factory2() as session:
            result = await session.execute(
                select(Holding).where(Holding.user_id == "demo")
            )
            total = len(result.scalars().all())
        await engine2.dispose()
        print(f"[seed_demo] 완료 — 신규 삽입: {inserted}건 / DB 총 보유종목: {total}건")
    except Exception:
        print(f"[seed_demo] 완료 — 신규 삽입: {inserted}건")


if __name__ == "__main__":
    asyncio.run(main())
