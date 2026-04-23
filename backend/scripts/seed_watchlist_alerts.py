"""워치리스트 알림 시드 스크립트 — Sprint-08 Phase 2-D.

UI mock 과 일치하는 2건을 INSERT:
  - NVDA > 550 (yahoo)
  - KRW-BTC < 70,000,000 (upbit)

이미 존재하면 중복 삽입하지 않음 (symbol+market+direction+threshold 기준).
"""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.models import WatchlistAlert  # noqa: E402

_SEED_ALERTS = [
    {
        "user_id": "demo",
        "symbol": "NVDA",
        "market": "yahoo",
        "direction": "above",
        "threshold": Decimal("550.0000"),
        "enabled": True,
    },
    {
        "user_id": "demo",
        "symbol": "KRW-BTC",
        "market": "upbit",
        "direction": "below",
        "threshold": Decimal("70000000.0000"),
        "enabled": True,
    },
]


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession() as session:
        for seed in _SEED_ALERTS:
            # 중복 확인
            existing = await session.execute(
                select(WatchlistAlert).where(
                    WatchlistAlert.user_id == seed["user_id"],
                    WatchlistAlert.symbol == seed["symbol"],
                    WatchlistAlert.market == seed["market"],
                    WatchlistAlert.direction == seed["direction"],
                    WatchlistAlert.threshold == seed["threshold"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                print(f"[SKIP] {seed['symbol']} {seed['direction']} {seed['threshold']} already exists")
                continue

            alert = WatchlistAlert(**seed)
            session.add(alert)
            print(f"[INSERT] {seed['symbol']} {seed['direction']} {seed['threshold']}")

        await session.commit()
        print("Done.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
