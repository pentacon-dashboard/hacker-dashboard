"""Integration tests — /users/me + /users/me/settings (sprint-08 B-6)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services import user_settings as svc


@pytest.fixture(autouse=True)
def reset_store():
    svc.reset_store()
    yield
    svc.reset_store()


class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_no_header_returns_demo_user(self, client: AsyncClient):
        resp = await client.get("/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "demo-user"
        assert data["name"] == "Demo User"
        assert data["email"] == "demo@demo.com"

    @pytest.mark.asyncio
    async def test_get_me_with_header_returns_custom_user_id(self, client: AsyncClient):
        resp = await client.get("/users/me", headers={"X-User-Id": "user-123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-123"


class TestGetSettings:
    @pytest.mark.asyncio
    async def test_get_settings_returns_default(self, client: AsyncClient):
        resp = await client.get("/users/me/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "demo-user"
        assert data["language"] == "ko"
        assert data["timezone"] == "Asia/Seoul"
        assert data["theme"]["mode"] == "system"
        assert data["notifications"]["email_alerts"] is True
        assert data["data"]["refresh_interval_sec"] == 60
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_settings_with_header(self, client: AsyncClient):
        resp = await client.get(
            "/users/me/settings", headers={"X-User-Id": "custom-user"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "custom-user"

    @pytest.mark.asyncio
    async def test_get_settings_idempotent(self, client: AsyncClient):
        resp1 = await client.get("/users/me/settings")
        resp2 = await client.get("/users/me/settings")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["updated_at"] == resp2.json()["updated_at"]


class TestPatchSettings:
    @pytest.mark.asyncio
    async def test_patch_name(self, client: AsyncClient):
        resp = await client.patch("/users/me/settings", json={"name": "Alice"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["language"] == "ko"  # 변경 안 됨

    @pytest.mark.asyncio
    async def test_patch_theme(self, client: AsyncClient):
        resp = await client.patch(
            "/users/me/settings",
            json={"theme": {"mode": "dark", "accent": "cyan"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"]["mode"] == "dark"
        assert data["theme"]["accent"] == "cyan"

    @pytest.mark.asyncio
    async def test_patch_notifications(self, client: AsyncClient):
        resp = await client.patch(
            "/users/me/settings",
            json={"notifications": {"push_alerts": True, "price_threshold_pct": 10.0}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"]["push_alerts"] is True
        assert data["notifications"]["price_threshold_pct"] == 10.0

    @pytest.mark.asyncio
    async def test_patch_empty_body_ok(self, client: AsyncClient):
        resp = await client.patch("/users/me/settings", json={})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_invalid_language_returns_422(self, client: AsyncClient):
        resp = await client.patch("/users/me/settings", json={"language": "zh"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_invalid_theme_mode_returns_422(self, client: AsyncClient):
        resp = await client.patch(
            "/users/me/settings",
            json={"theme": {"mode": "invalid_mode"}},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_with_header(self, client: AsyncClient):
        resp = await client.patch(
            "/users/me/settings",
            json={"name": "Bob"},
            headers={"X-User-Id": "user-abc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-abc"
        assert data["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_patch_persists_across_get(self, client: AsyncClient):
        await client.patch("/users/me/settings", json={"name": "Persisted"})
        resp = await client.get("/users/me/settings")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Persisted"
