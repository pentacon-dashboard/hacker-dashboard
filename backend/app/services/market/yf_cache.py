"""yfinance 호출 결과 in-memory TTL 캐시.

asyncio.Lock 으로 동시 갱신 방지.
Redis 캐시(market/cache.py)와 별도 계층 — yfinance 전용.

TTL 정책:
  - 지수/섹터/원자재: 60초
  - 종목 quote: 10초
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# { key: (data, expire_at) }
_store: dict[str, tuple[Any, float]] = {}
_lock = asyncio.Lock()


async def yf_cache_get(key: str) -> Any | None:
    """캐시 조회. 만료됐거나 없으면 None 반환."""
    entry = _store.get(key)
    if entry is None:
        return None
    data, expire_at = entry
    if time.monotonic() > expire_at:
        _store.pop(key, None)
        return None
    return data


async def yf_cache_set(key: str, data: Any, ttl: int) -> None:
    """캐시 저장."""
    async with _lock:
        _store[key] = (data, time.monotonic() + ttl)


def yf_cache_clear() -> None:
    """테스트 격리용 전체 초기화."""
    _store.clear()
