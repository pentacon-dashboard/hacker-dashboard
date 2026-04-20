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
import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["infra"])


class ServiceStatus(BaseModel):
    db: str
    redis: str


class HealthResponse(BaseModel):
    status: str
    services: ServiceStatus
    uptime_seconds: int
    version: str


async def _check_db() -> str:
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=2.0)
        return "ok"
    except Exception:
        return "unreachable"


async def _check_redis() -> str:
    try:
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await asyncio.wait_for(client.ping(), timeout=2.0)
        await client.aclose()
        return "ok"
    except Exception:
        return "unreachable"


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    db_status, redis_status = await asyncio.gather(_check_db(), _check_redis())

    overall = (
        "ok"
        if db_status == "ok" and redis_status == "ok"
        else "degraded"
    )

    # uptime: lifespan 에서 저장한 started_at 사용
    started_at: float | None = getattr(request.app.state, "started_at", None)
    uptime_seconds = int(time.time() - started_at) if started_at is not None else 0

    return HealthResponse(
        status=overall,
        services=ServiceStatus(db=db_status, redis=redis_status),
        uptime_seconds=uptime_seconds,
        version=settings.app_version,
    )
