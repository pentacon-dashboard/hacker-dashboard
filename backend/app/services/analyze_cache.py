"""
분석 결과 캐시 서비스.

우선순위:
1. Redis (redis_url 연결 가능 시)
2. in-memory LRU (128 항목, Redis 미연결 시 폴백)

캐시 키:
- /analyze: sha256(AnalyzeRequest.model_dump_json())
- /analyze/csv: sha256(파일 바이트 + user_note)

TTL: 5분 (300초)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any

import redis.asyncio as aioredis

from app.core.config import DEFAULT_REDIS_URL, settings
from app.core.logging import logger

_TTL_SECONDS = 300
_LRU_MAXSIZE = 128

# in-memory LRU: key → (value_json, expire_at)
_lru: OrderedDict[str, tuple[str, float]] = OrderedDict()

# Redis 연결 싱글턴 (lazy)
_redis_client: aioredis.Redis | None = None
_redis_available: bool | None = None  # None = 아직 검사 안 함


def _configured_redis_url() -> str | None:
    redis_url = settings.redis_url.strip()
    if not redis_url:
        return None
    if redis_url == DEFAULT_REDIS_URL and "REDIS_URL" not in os.environ:
        return None
    return redis_url


async def _get_redis() -> aioredis.Redis | None:
    """Redis 연결 반환. 연결 불가 시 None."""
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is None:
        redis_url = _configured_redis_url()
        if redis_url is None:
            _redis_available = False
            logger.info("analyze_cache: Redis not configured, using LRU")
            return None
        try:
            client: aioredis.Redis = aioredis.from_url(
                redis_url,
                socket_connect_timeout=1,
                socket_timeout=1,
                decode_responses=True,
            )
            await client.ping()  # type: ignore[misc]
            _redis_client = client
            _redis_available = True
            logger.info("analyze_cache: Redis connected")
        except Exception as exc:
            logger.warning("analyze_cache: Redis unavailable, falling back to LRU — %s", exc)
            _redis_available = False
            return None
    return _redis_client


# ── LRU 헬퍼 ──────────────────────────────────────────────────────────────────


def _lru_get(key: str) -> str | None:
    entry = _lru.get(key)
    if entry is None:
        return None
    value_json, expire_at = entry
    if time.monotonic() > expire_at:
        del _lru[key]
        return None
    # MRU 로 이동
    _lru.move_to_end(key)
    return value_json


def _lru_set(key: str, value_json: str) -> None:
    expire_at = time.monotonic() + _TTL_SECONDS
    _lru[key] = (value_json, expire_at)
    _lru.move_to_end(key)
    # 크기 초과 시 가장 오래된 항목 제거
    while len(_lru) > _LRU_MAXSIZE:
        _lru.popitem(last=False)


# ── 공개 API ──────────────────────────────────────────────────────────────────


def make_request_key(request_json: str, portfolio_hash: str = "") -> str:
    """AnalyzeRequest.model_dump_json() 문자열 → 캐시 키.

    portfolio_hash: 포트폴리오 컨텍스트가 있을 때 앞 16자 SHA-256 해시를 섞어 기존 캐시와 분리.
    없으면 빈 문자열 → 기존 캐시 그대로 사용.
    """
    raw = request_json + portfolio_hash
    return hashlib.sha256(raw.encode()).hexdigest()


def make_csv_key(file_bytes: bytes, user_note: str) -> str:
    """CSV 파일 바이트 + user_note → 캐시 키."""
    h = hashlib.sha256(file_bytes)
    h.update(user_note.encode())
    return h.hexdigest()


async def cache_get(key: str) -> dict[str, Any] | None:
    """캐시에서 분석 결과 조회. HIT 시 dict 반환, MISS 시 None."""
    redis = await _get_redis()
    if redis is not None:
        try:
            raw = await redis.get(f"analyze:{key}")
            if raw is not None:
                result: dict[str, Any] = json.loads(raw)
                return result
        except Exception as exc:
            logger.warning("analyze_cache: Redis GET failed — %s", exc)
            # Redis 오류 시 LRU 로 폴백
    # LRU 조회
    raw_lru = _lru_get(key)
    if raw_lru is not None:
        lru_result: dict[str, Any] = json.loads(raw_lru)
        return lru_result
    return None


async def cache_set(key: str, value: dict[str, Any]) -> None:
    """분석 결과를 캐시에 저장 (TTL 5분)."""
    value_json = json.dumps(value, ensure_ascii=False)
    redis = await _get_redis()
    if redis is not None:
        try:
            await redis.set(f"analyze:{key}", value_json, ex=_TTL_SECONDS)
            return
        except Exception as exc:
            logger.warning("analyze_cache: Redis SET failed — %s", exc)
    # LRU 폴백
    _lru_set(key, value_json)


def reset_for_testing() -> None:
    """테스트 격리용 — LRU 초기화 및 Redis 연결 상태 리셋."""
    global _redis_client, _redis_available
    _lru.clear()
    _redis_client = None
    _redis_available = None
