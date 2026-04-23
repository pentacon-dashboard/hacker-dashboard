"""FxAdapter 단위 테스트 — respx 로 exchangerate.host mock."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.services.fx import _FALLBACK_RATES, FxAdapter


@pytest.fixture
def fx() -> FxAdapter:
    """테스트용 FxAdapter 인스턴스 (전역 싱글턴과 분리)."""
    import app.services.fx as fx_module

    instance = FxAdapter()
    # 전역 in-memory 캐시 초기화 (테스트 간 격리)
    fx_module._mem_store.clear()
    return instance


@pytest.mark.asyncio
async def test_same_currency_returns_one(fx: FxAdapter) -> None:
    """동일 통화는 1.0 반환."""
    rate = await fx.get_rate("KRW", "KRW")
    assert rate == 1.0


@pytest.mark.asyncio
async def test_usdt_treated_as_usd(fx: FxAdapter) -> None:
    """USDT → KRW 는 USD → KRW 와 동일한 환율 반환 (폴백)."""
    rate_usdt = await fx.get_rate("USDT", "KRW")
    rate_usd = await fx.get_rate("USD", "KRW")
    # 폴백에서 동일 값이어야 함
    assert abs(rate_usdt - rate_usd) < 0.01


@pytest.mark.asyncio
@respx.mock
async def test_fetch_from_api_success(fx: FxAdapter) -> None:
    """exchangerate.host 정상 응답 파싱."""
    respx.get("https://api.exchangerate.host/convert").mock(
        return_value=httpx.Response(
            200,
            json={"result": 1380.5, "success": True},
        )
    )
    client = httpx.AsyncClient()
    fx.set_http_client(client)
    rate = await fx.get_rate("USD", "KRW")
    await client.aclose()
    assert abs(rate - 1380.5) < 0.01


@pytest.mark.asyncio
@respx.mock
async def test_fetch_from_api_failure_falls_back(fx: FxAdapter) -> None:
    """API 실패 시 폴백 테이블 환율 반환."""
    respx.get("https://api.exchangerate.host/convert").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    client = httpx.AsyncClient()
    fx.set_http_client(client)
    rate = await fx.get_rate("USD", "KRW")
    await client.aclose()
    # 폴백값 1350.0 ± 1
    assert abs(rate - 1350.0) < 1.0


@pytest.mark.asyncio
@respx.mock
async def test_network_timeout_falls_back(fx: FxAdapter) -> None:
    """네트워크 타임아웃 시 폴백 테이블 환율 반환."""
    respx.get("https://api.exchangerate.host/convert").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    client = httpx.AsyncClient()
    fx.set_http_client(client)
    rate = await fx.get_rate("EUR", "KRW")
    await client.aclose()
    assert rate > 0


@pytest.mark.asyncio
async def test_redis_cache_hit(fx: FxAdapter) -> None:
    """Redis 캐시 히트 시 API 호출 없이 반환."""

    class MockRedis:
        async def get(self, key: str) -> str | None:
            if "USD:KRW" in key:
                return "1400.0"
            return None

        async def set(self, key: str, val: str, ex: int | None = None) -> None:
            pass

    fx.set_redis(MockRedis())
    rate = await fx.get_rate("USD", "KRW")
    assert abs(rate - 1400.0) < 0.01


@pytest.mark.asyncio
async def test_redis_unavailable_uses_fallback(fx: FxAdapter) -> None:
    """Redis None 시 in-memory → 폴백 경로."""
    # redis 없이 API 도 없이 호출 — 폴백 테이블 사용
    rate = await fx.get_rate("JPY", "KRW")
    assert rate > 0


def test_fallback_table_completeness() -> None:
    """폴백 테이블에 핵심 통화 쌍이 존재하는지 확인."""
    required = [("USD", "KRW"), ("EUR", "KRW"), ("JPY", "KRW"), ("USDT", "KRW")]
    for pair in required:
        assert pair in _FALLBACK_RATES, f"폴백 테이블에 {pair} 누락"


@pytest.mark.asyncio
async def test_inverse_fallback(fx: FxAdapter) -> None:
    """역방향 환율 계산 정확성."""
    usd_to_krw = await fx.get_rate("USD", "KRW")
    krw_to_usd = await fx.get_rate("KRW", "USD")
    # 역수 관계 확인 (오차 허용)
    assert abs(usd_to_krw * krw_to_usd - 1.0) < 0.05
