"""
analyze_cache 서비스 단위 테스트.

- HIT/MISS 동작 (in-memory LRU — Redis 없는 환경)
- TTL 만료 (time.monotonic 패치)
- make_request_key / make_csv_key 해시 일관성
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.services import analyze_cache


@pytest.fixture(autouse=True)
async def reset_cache():
    """각 테스트 전 캐시와 Redis 연결 상태를 초기화.

    LRU 단위 테스트(TTL·eviction)는 Redis 미사용 강제.
    X-Cache 통합 테스트는 Redis FLUSHDB 로 이전 데이터를 제거하여 격리.
    """
    analyze_cache.reset_for_testing()
    # LRU 단위 테스트: Redis 미사용 강제 (기본값 — 개별 통합 테스트에서 재연결 가능)
    analyze_cache._redis_available = False
    yield
    # 이전 테스트가 Redis 를 활성화했을 수 있으므로 연결이 있으면 analyze:* 키 정리
    if analyze_cache._redis_client is not None:
        try:
            keys = await analyze_cache._redis_client.keys("analyze:*")
            if keys:
                await analyze_cache._redis_client.delete(*keys)
        except Exception:
            pass
    analyze_cache.reset_for_testing()


# ── 기본 HIT/MISS ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_miss_on_empty() -> None:
    """캐시가 비어 있으면 MISS(None) 반환."""
    result = await analyze_cache.cache_get("nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_then_get_hit() -> None:
    """set 후 get → HIT (동일 dict 반환)."""
    key = "test_key_hit"
    value = {"status": "ok", "result": {"asset_class": "stock"}, "meta": {}}
    await analyze_cache.cache_set(key, value)
    result = await analyze_cache.cache_get(key)
    assert result is not None
    assert result["status"] == "ok"
    assert result["result"]["asset_class"] == "stock"


@pytest.mark.asyncio
async def test_cache_different_keys_independent() -> None:
    """서로 다른 키는 독립적으로 저장/조회된다."""
    await analyze_cache.cache_set("key_a", {"val": 1})
    await analyze_cache.cache_set("key_b", {"val": 2})

    a = await analyze_cache.cache_get("key_a")
    b = await analyze_cache.cache_get("key_b")

    assert a is not None and a["val"] == 1
    assert b is not None and b["val"] == 2


# ── TTL 만료 ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_ttl_expiry() -> None:
    """TTL 이 지나면 MISS."""
    key = "ttl_key"
    await analyze_cache.cache_set(key, {"data": "will_expire"})

    # TTL 300초 뒤로 시간 점프
    future_time = time.monotonic() + 400
    with patch("app.services.analyze_cache.time") as mock_time:
        mock_time.monotonic.return_value = future_time
        result = analyze_cache._lru_get(key)

    assert result is None


@pytest.mark.asyncio
async def test_cache_not_expired_before_ttl() -> None:
    """TTL 이 지나기 전에는 HIT."""
    key = "ttl_key_fresh"
    await analyze_cache.cache_set(key, {"data": "still_valid"})

    # 100초 후 (TTL 300초)
    near_future = time.monotonic() + 100
    with patch("app.services.analyze_cache.time") as mock_time:
        mock_time.monotonic.return_value = near_future
        result = analyze_cache._lru_get(key)

    assert result is not None


# ── LRU 용량 제한 ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lru_eviction_when_full() -> None:
    """128개 초과 시 가장 오래된 항목 제거."""
    # 129개 삽입
    for i in range(analyze_cache._LRU_MAXSIZE + 1):
        await analyze_cache.cache_set(f"evict_key_{i}", {"i": i})

    # 가장 처음 삽입된 key_0 이 제거되어야 함
    first_result = await analyze_cache.cache_get("evict_key_0")
    assert first_result is None

    # 마지막 삽입된 항목은 존재
    last_result = await analyze_cache.cache_get(f"evict_key_{analyze_cache._LRU_MAXSIZE}")
    assert last_result is not None


# ── 키 생성 함수 ──────────────────────────────────────────────────────────────


def test_make_request_key_deterministic() -> None:
    """같은 JSON → 같은 키."""
    k1 = analyze_cache.make_request_key('{"query": "test", "data": []}')
    k2 = analyze_cache.make_request_key('{"query": "test", "data": []}')
    assert k1 == k2
    assert len(k1) == 64  # sha256 hex


def test_make_request_key_different_inputs() -> None:
    """다른 JSON → 다른 키."""
    k1 = analyze_cache.make_request_key('{"query": "test1"}')
    k2 = analyze_cache.make_request_key('{"query": "test2"}')
    assert k1 != k2


def test_make_csv_key_deterministic() -> None:
    """같은 바이트 + 같은 user_note → 같은 키."""
    data = b"col1,col2\nval1,val2\n"
    k1 = analyze_cache.make_csv_key(data, "note")
    k2 = analyze_cache.make_csv_key(data, "note")
    assert k1 == k2


def test_make_csv_key_different_notes() -> None:
    """같은 파일 다른 user_note → 다른 키."""
    data = b"col1,col2\nval1,val2\n"
    k1 = analyze_cache.make_csv_key(data, "note_a")
    k2 = analyze_cache.make_csv_key(data, "note_b")
    assert k1 != k2


def test_make_csv_key_different_files() -> None:
    """다른 파일 같은 note → 다른 키."""
    k1 = analyze_cache.make_csv_key(b"aaa\nbbb\n", "note")
    k2 = analyze_cache.make_csv_key(b"ccc\nddd\n", "note")
    assert k1 != k2


# ── API 응답 X-Cache 헤더 통합 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_endpoint_x_cache_miss_then_hit(fake_llm_client) -> None:
    """
    /analyze 엔드포인트: 첫 번째 요청 MISS, 두 번째 동일 요청 HIT.

    Redis 가 실행 중이면 FLUSHDB 로 이전 데이터를 제거하고 LRU 폴백으로 테스트한다.
    """
    import uuid

    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # Redis가 실행 중이더라도 LRU 경로로 강제하여 데이터 잔여 없이 격리
    analyze_cache.reset_for_testing()
    analyze_cache._redis_available = False  # LRU 전용 모드

    # 매 실행마다 고유한 query 로 캐시 충돌 방지
    unique_query = f"cache_test_unique_xyz_{uuid.uuid4().hex}"
    payload = {
        "data": [{"symbol": "AAPL", "price": 180.0}],
        "query": unique_query,
        "asset_class_hint": "stock",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp1 = await ac.post("/analyze", json=payload)
        resp2 = await ac.post("/analyze", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.headers.get("X-Cache") == "MISS"
    assert resp2.headers.get("X-Cache") == "HIT"
