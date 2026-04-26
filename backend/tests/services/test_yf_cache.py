"""yf_cache in-memory TTL 캐시 단위 테스트."""

from __future__ import annotations

import pytest

from app.services.market.yf_cache import yf_cache_clear, yf_cache_get, yf_cache_set


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    yf_cache_clear()
    yield
    yf_cache_clear()


@pytest.mark.asyncio
async def test_cache_miss_returns_none() -> None:
    result = await yf_cache_get("nonexistent:key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get() -> None:
    await yf_cache_set("test:key", {"price": 42.0}, ttl=60)
    result = await yf_cache_get("test:key")
    assert result is not None
    assert result["price"] == 42.0


@pytest.mark.asyncio
async def test_cache_expires_after_ttl() -> None:
    """TTL 0 으로 설정하면 즉시 만료."""
    import time as _time

    from app.services.market import yf_cache as _mod

    # 과거 시각으로 expire_at 직접 삽입
    _mod._store["expiry:key"] = ({"v": 1}, _time.monotonic() - 1.0)
    result = await yf_cache_get("expiry:key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_overwrite() -> None:
    await yf_cache_set("dup:key", {"v": 1}, ttl=60)
    await yf_cache_set("dup:key", {"v": 2}, ttl=60)
    result = await yf_cache_get("dup:key")
    assert result == {"v": 2}


@pytest.mark.asyncio
async def test_cache_clear_removes_all() -> None:
    await yf_cache_set("a", 1, ttl=60)
    await yf_cache_set("b", 2, ttl=60)
    yf_cache_clear()
    assert await yf_cache_get("a") is None
    assert await yf_cache_get("b") is None
