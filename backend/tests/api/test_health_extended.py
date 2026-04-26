"""
/health 확장 필드 테스트 (Week-4).

검증 항목:
  - uptime_seconds 필드 존재 + 양수
  - version 필드 존재 + 비어있지 않음
  - 기존 status / services 필드 유지
  - 두 번째 요청에서 uptime_seconds 가 0 이상임을 확인 (단조 증가는 실시간으로 검증)
"""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_uptime_field_exists(client: AsyncClient) -> None:
    """uptime_seconds 필드가 응답에 존재한다."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_health_uptime_is_non_negative(client: AsyncClient) -> None:
    """uptime_seconds 는 0 이상 정수."""
    resp = await client.get("/health")
    body = resp.json()
    uptime = body["uptime_seconds"]
    assert isinstance(uptime, int)
    assert uptime >= 0


@pytest.mark.asyncio
async def test_health_uptime_increases(client: AsyncClient) -> None:
    """두 번째 요청의 uptime 이 첫 번째 이상 (단조 비감소)."""
    resp1 = await client.get("/health")
    time.sleep(0.05)  # 50ms 대기
    resp2 = await client.get("/health")

    uptime1 = resp1.json()["uptime_seconds"]
    uptime2 = resp2.json()["uptime_seconds"]
    assert uptime2 >= uptime1


@pytest.mark.asyncio
async def test_health_version_field_exists(client: AsyncClient) -> None:
    """version 필드가 응답에 존재한다."""
    resp = await client.get("/health")
    body = resp.json()
    assert "version" in body


@pytest.mark.asyncio
async def test_health_version_is_string(client: AsyncClient) -> None:
    """version 필드는 비어있지 않은 문자열."""
    resp = await client.get("/health")
    body = resp.json()
    assert isinstance(body["version"], str)
    assert len(body["version"]) > 0


@pytest.mark.asyncio
async def test_health_version_format(client: AsyncClient) -> None:
    """version 은 semver 형식 (major.minor.patch)."""
    import re

    resp = await client.get("/health")
    version = resp.json()["version"]
    assert re.match(r"^\d+\.\d+\.\d+", version), f"버전 형식 오류: {version!r}"


@pytest.mark.asyncio
async def test_health_existing_fields_preserved(client: AsyncClient) -> None:
    """기존 status / services 필드가 여전히 존재한다."""
    resp = await client.get("/health")
    body = resp.json()
    assert "status" in body
    assert "services" in body
    assert "db" in body["services"]
    assert "redis" in body["services"]


@pytest.mark.asyncio
async def test_health_status_valid_value(client: AsyncClient) -> None:
    """status 는 ok 또는 degraded."""
    resp = await client.get("/health")
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
