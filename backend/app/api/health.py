"""
/health 엔드포인트.

응답 필드:
  - status: ok | degraded
  - services: {db, redis}
  - uptime_seconds: int (앱 시작 이후 경과 시간)
  - version: str (pyproject.toml 또는 APP_VERSION 환경변수)
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import redis.asyncio as aioredis
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.core.config import DEFAULT_REDIS_URL, settings
from app.db.session import engine

router = APIRouter(tags=["infra"])

_CHECK_TIMEOUT_SECONDS = 2.0
_REQUIRED_DB_TABLES = frozenset(
    {
        "alembic_version",
        "users",
        "watchlist_items",
        "holdings",
        "portfolio_snapshots",
        "documents",
        "document_chunks",
        "copilot_sessions",
        "copilot_turns",
        "watchlist_alerts",
        "user_settings",
    }
)


class _DbSchemaError(RuntimeError):
    pass


class ServiceStatus(BaseModel):
    db: str
    redis: str


class HealthResponse(BaseModel):
    status: str
    services: ServiceStatus
    uptime_seconds: int
    version: str


@lru_cache(maxsize=1)
def _expected_alembic_head() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    head = ScriptDirectory.from_config(config).get_current_head()
    return str(head)


def _validate_db_schema(
    existing_tables: frozenset[str] | set[str], alembic_version: str | None
) -> None:
    missing_tables = sorted(_REQUIRED_DB_TABLES - set(existing_tables))
    if missing_tables:
        raise _DbSchemaError(f"missing tables: {', '.join(missing_tables)}")

    expected_head = _expected_alembic_head()
    if alembic_version != expected_head:
        raise _DbSchemaError(
            f"alembic version mismatch: expected {expected_head}, got {alembic_version or 'none'}"
        )


def _load_db_schema_state(sync_conn: Connection) -> tuple[frozenset[str], str | None]:
    inspector = inspect(sync_conn)
    tables = frozenset(inspector.get_table_names())
    version_value = sync_conn.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one_or_none()
    return tables, str(version_value) if version_value is not None else None


async def _ping_db() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        existing_tables, alembic_version = await conn.run_sync(_load_db_schema_state)
        _validate_db_schema(existing_tables, alembic_version)


async def _check_db() -> str:
    try:
        await asyncio.wait_for(_ping_db(), timeout=_CHECK_TIMEOUT_SECONDS)
        return "ok"
    except _DbSchemaError:
        return "schema_mismatch"
    except Exception:
        return "unreachable"


def _configured_redis_url() -> str | None:
    redis_url = settings.redis_url.strip()
    if not redis_url:
        return None
    if redis_url == DEFAULT_REDIS_URL and "REDIS_URL" not in os.environ:
        return None
    return redis_url


async def _ping_redis() -> None:
    redis_url = _configured_redis_url()
    if redis_url is None:
        return

    client = aioredis.from_url(
        redis_url,
        socket_connect_timeout=_CHECK_TIMEOUT_SECONDS,
        socket_timeout=_CHECK_TIMEOUT_SECONDS,
    )
    try:
        await cast(Awaitable[Any], client.ping())
    finally:
        await client.aclose()


async def _check_redis() -> str:
    if _configured_redis_url() is None:
        return "disabled"

    try:
        await asyncio.wait_for(_ping_redis(), timeout=_CHECK_TIMEOUT_SECONDS)
        return "ok"
    except Exception:
        return "unreachable"


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    db_status, redis_status = await asyncio.gather(_check_db(), _check_redis())

    redis_healthy = redis_status in {"ok", "disabled"}
    overall = "ok" if db_status == "ok" and redis_healthy else "degraded"

    # uptime: lifespan 에서 저장한 started_at 사용
    started_at: float | None = getattr(request.app.state, "started_at", None)
    uptime_seconds = int(time.time() - started_at) if started_at is not None else 0

    return HealthResponse(
        status=overall,
        services=ServiceStatus(db=db_status, redis=redis_status),
        uptime_seconds=uptime_seconds,
        version=settings.app_version,
    )
