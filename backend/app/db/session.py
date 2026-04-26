from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# BACKEND_DB_POOL_DISABLE=1 또는 sqlite URL 일 때 NullPool 사용 (harness 격리용)
_db_url: str = settings.database_url
_is_sqlite = _db_url.startswith("sqlite")
_pool_disable = os.environ.get("BACKEND_DB_POOL_DISABLE", "0") == "1"

if _is_sqlite or _pool_disable:
    # SQLite / in-memory 격리 환경: 연결 풀 비활성화
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        _db_url,
        echo=settings.debug,
        poolclass=NullPool,
    )
else:
    # PostgreSQL 운영 환경: 연결 풀 유지 (Neon serverless 에서는 pool_size 작게 유지)
    engine = create_async_engine(
        _db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
