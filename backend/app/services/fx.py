"""환율 어댑터 — FxAdapter.

- exchangerate.host (무료 API) 호출
- KRW/USD/EUR/JPY 지원
- Redis 캐시 TTL 1h. Redis 미연결 시 in-memory LRU fallback
- 네트워크 실패 시 하드코딩 폴백 테이블 반환 (데모 안정성)
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 폴백 환율 테이블 (데모 안정성 보장)
_FALLBACK_RATES: dict[tuple[str, str], float] = {
    ("USD", "KRW"): 1350.0,
    ("KRW", "USD"): 1 / 1350.0,
    ("EUR", "KRW"): 1470.0,
    ("KRW", "EUR"): 1 / 1470.0,
    ("JPY", "KRW"): 9.0,
    ("KRW", "JPY"): 1 / 9.0,
    ("EUR", "USD"): 1.09,
    ("USD", "EUR"): 1 / 1.09,
    ("JPY", "USD"): 0.0067,
    ("USD", "JPY"): 149.0,
    ("USDT", "KRW"): 1350.0,
    ("KRW", "USDT"): 1 / 1350.0,
    ("USDT", "USD"): 1.0,
    ("USD", "USDT"): 1.0,
}

_SUPPORTED = {"KRW", "USD", "EUR", "JPY", "USDT"}

# exchangerate.host 엔드포인트 (무료, API key 불필요)
_API_URL = "https://api.exchangerate.host/convert"


# ────────────── in-memory LRU fallback (Redis 미연결 시) ──────────────

@lru_cache(maxsize=64)
def _mem_cache_get(key: str) -> float | None:  # pragma: no cover
    """lru_cache 는 TTL 없음 — 단순 데모 캐시."""
    return None  # 항상 캐시 미스 (실제 캐시는 _mem_store 딕셔너리가 담당)


_mem_store: dict[str, float] = {}


class FxAdapter:
    """환율 어댑터 싱글턴."""

    _instance: "FxAdapter | None" = None

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client
        self._redis: Any | None = None  # aioredis.Redis — 지연 주입

    @classmethod
    def get_instance(cls) -> "FxAdapter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_http_client(self, client: httpx.AsyncClient | None) -> None:
        self._client = client

    def set_redis(self, redis: Any) -> None:
        self._redis = redis

    def clear_mem_cache(self) -> None:
        """in-memory 캐시 초기화 (테스트용)."""
        _mem_store.clear()

    # ────────────── public API ──────────────

    async def get_rate(self, base: str, quote: str) -> float:
        """base → quote 환율 반환. 예) get_rate("USD", "KRW") → 1350.0."""
        base = base.upper()
        quote = quote.upper()

        if base == quote:
            return 1.0

        # USDT 는 USD 로 취급
        effective_base = "USD" if base == "USDT" else base
        effective_quote = "USD" if quote == "USDT" else quote

        if effective_base == effective_quote:
            return 1.0

        cache_key = f"fx:{effective_base}:{effective_quote}"

        # 1) Redis 캐시
        cached = await self._redis_get(cache_key)
        if cached is not None:
            return cached

        # 2) in-memory
        if cache_key in _mem_store:
            return _mem_store[cache_key]

        # 3) 외부 API
        rate = await self._fetch_from_api(effective_base, effective_quote)
        if rate is None:
            # 4) 폴백 테이블
            rate = self._fallback(effective_base, effective_quote)

        await self._redis_set(cache_key, rate, ttl=3600)
        _mem_store[cache_key] = rate
        return rate

    # ────────────── 내부 헬퍼 ──────────────

    async def _fetch_from_api(self, base: str, quote: str) -> float | None:
        """exchangerate.host /convert 호출."""
        client = self._client
        created_local = False
        if client is None:
            client = httpx.AsyncClient(timeout=5.0)
            created_local = True
        try:
            resp = await client.get(
                _API_URL,
                params={"from": base, "to": quote, "amount": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result") or data.get("info", {}).get("rate")
            if result and float(result) > 0:
                return float(result)
            return None
        except Exception as exc:
            logger.warning("FX API 호출 실패 (%s→%s): %s", base, quote, exc)
            return None
        finally:
            if created_local:
                await client.aclose()

    def _fallback(self, base: str, quote: str) -> float:
        """하드코딩 폴백 테이블에서 환율 조회. 없으면 1.0 반환."""
        direct = _FALLBACK_RATES.get((base, quote))
        if direct:
            return direct
        # 역방향
        inverse = _FALLBACK_RATES.get((quote, base))
        if inverse:
            return 1.0 / inverse
        # USD 경유 교차 환율
        base_to_usd = _FALLBACK_RATES.get((base, "USD"), 1.0)
        usd_to_quote = _FALLBACK_RATES.get(("USD", quote), 1.0)
        return base_to_usd * usd_to_quote

    async def _redis_get(self, key: str) -> float | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            return float(raw) if raw is not None else None
        except Exception as exc:
            logger.debug("Redis FX GET 실패: %s", exc)
            return None

    async def _redis_set(self, key: str, value: float, ttl: int) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(key, str(value), ex=ttl)
        except Exception as exc:
            logger.debug("Redis FX SET 실패: %s", exc)


# 전역 싱글턴
fx_adapter = FxAdapter.get_instance()


async def get_rate(base: str, quote: str) -> float:
    """모듈 레벨 편의 함수."""
    return await fx_adapter.get_rate(base, quote)
