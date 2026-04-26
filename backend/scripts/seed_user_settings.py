"""사용자 설정 시드 스크립트 — migration 006.

demo-user 행이 없으면 기본값으로 INSERT.
이미 존재하면 스킵 (멱등).

사용:
  uv run python scripts/seed_user_settings.py
"""
from __future__ import annotations

import asyncio
import datetime
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.models import UserSettings  # noqa: E402

_DEMO_USER_ID = "demo-user"

_SEED_ROW = {
    "user_id": _DEMO_USER_ID,
    "name": "Demo User",
    "email": "demo@demo.com",
    "language": "ko",
    "timezone": "Asia/Seoul",
    "theme": {"mode": "system", "accent": "violet"},
    "notifications": {
        "email_alerts": True,
        "push_alerts": False,
        "price_threshold_pct": 5.0,
        "daily_digest": True,
    },
    "data": {
        "refresh_interval_sec": 60,
        "auto_refresh": True,
        "auto_backup": False,
        "cache_size_mb": 256,
    },
    "connected_accounts": [
        {
            "provider": "google",
            "email": "demo@demo.com",
            "connected_at": "2026-01-01T00:00:00Z",
        }
    ],
    "updated_at": datetime.datetime.now(datetime.UTC),
}


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == _DEMO_USER_ID)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            print(f"[SKIP] user_settings row for '{_DEMO_USER_ID}' already exists.")
        else:
            row = UserSettings(**_SEED_ROW)
            session.add(row)
            await session.commit()
            print(f"[INSERT] user_settings row for '{_DEMO_USER_ID}' created.")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
