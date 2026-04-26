"""Redis 캐시 레이어.

- Quote: TTL 5s
- OHLC: TTL 60s
- Redis 미연결 시 passthrough (예외 삼키고 None 반환)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1,
            )
        except Exception as exc:
            logger.warning("Redis 초기화 실패 (passthrough 모드): %s", exc)
    return _redis_client


def set_redis(client: aioredis.Redis | None) -> None:
    """테스트 DI 주입."""
    global _redis_client
    _redis_client = client


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.debug("Redis GET 실패 (passthrough): %s", exc)
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except Exception as exc:
        logger.debug("Redis SET 실패 (passthrough): %s", exc)


def quote_key(market: str, symbol: str) -> str:
    return f"quote:{market}:{symbol}"


def ohlc_key(market: str, symbol: str, interval: str, limit: int) -> str:
    return f"ohlc:{market}:{symbol}:{interval}:{limit}"
