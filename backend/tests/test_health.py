import asyncio

import pytest
from httpx import AsyncClient

from app.api import health as health_module


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_has_status_field(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()
    assert "status" in body
    # DB/Redis 없는 환경이므로 degraded 또는 ok 모두 허용
    assert body["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_has_services_field(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()
    assert "services" in body
    assert "db" in body["services"]
    assert "redis" in body["services"]


@pytest.mark.asyncio
async def test_db_check_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_ping() -> None:
        await asyncio.sleep(1)

    monkeypatch.setattr(health_module, "_CHECK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(health_module, "_ping_db", slow_ping)

    assert await health_module._check_db() == "unreachable"


@pytest.mark.asyncio
async def test_redis_check_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_ping() -> None:
        await asyncio.sleep(1)

    monkeypatch.setattr(health_module, "_CHECK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(health_module, "_ping_redis", slow_ping)

    assert await health_module._check_redis() == "unreachable"
