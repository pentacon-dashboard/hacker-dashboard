import pytest
from httpx import AsyncClient


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
