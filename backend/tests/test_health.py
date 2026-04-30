import asyncio
import time
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api import health as health_module
from app.core.config import DEFAULT_REDIS_URL


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
async def test_db_check_reports_schema_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def schema_mismatch() -> None:
        raise health_module._DbSchemaError("missing table: holdings")

    monkeypatch.setattr(health_module, "_ping_db", schema_mismatch)

    assert await health_module._check_db() == "schema_mismatch"


def test_db_schema_validation_requires_core_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_module, "_expected_alembic_head", lambda: "head")

    with pytest.raises(health_module._DbSchemaError, match="missing tables"):
        health_module._validate_db_schema({"alembic_version", "holdings"}, "head")


def test_db_schema_validation_requires_current_alembic_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_module, "_expected_alembic_head", lambda: "head")

    with pytest.raises(health_module._DbSchemaError, match="alembic version mismatch"):
        health_module._validate_db_schema(health_module._REQUIRED_DB_TABLES, "old")


@pytest.mark.asyncio
async def test_redis_check_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_ping() -> None:
        await asyncio.sleep(1)

    monkeypatch.setenv("REDIS_URL", "redis://redis.example:6379/0")
    monkeypatch.setattr(health_module.settings, "redis_url", "redis://redis.example:6379/0")
    monkeypatch.setattr(health_module, "_CHECK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(health_module, "_ping_redis", slow_ping)

    assert await health_module._check_redis() == "unreachable"


@pytest.mark.asyncio
async def test_redis_check_disabled_when_url_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def ping_redis() -> None:
        nonlocal called
        called = True

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(health_module.settings, "redis_url", DEFAULT_REDIS_URL)
    monkeypatch.setattr(health_module, "_ping_redis", ping_redis)

    assert await health_module._check_redis() == "disabled"
    assert called is False


@pytest.mark.asyncio
async def test_health_ok_when_optional_redis_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok_db() -> str:
        return "ok"

    async def disabled_redis() -> str:
        return "disabled"

    monkeypatch.setattr(health_module, "_check_db", ok_db)
    monkeypatch.setattr(health_module, "_check_redis", disabled_redis)

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(started_at=time.time())))
    response = await health_module.health(request)

    assert response.status == "ok"
    assert response.services.redis == "disabled"


@pytest.mark.asyncio
async def test_health_degraded_when_db_schema_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def schema_mismatch_db() -> str:
        return "schema_mismatch"

    async def disabled_redis() -> str:
        return "disabled"

    monkeypatch.setattr(health_module, "_check_db", schema_mismatch_db)
    monkeypatch.setattr(health_module, "_check_redis", disabled_redis)

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(started_at=time.time())))
    response = await health_module.health(request)

    assert response.status == "degraded"
    assert response.services.db == "schema_mismatch"
