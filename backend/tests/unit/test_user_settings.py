"""Unit tests — user_settings 서비스 (migration 006: DB 기반).

SQLite in-memory DB 를 사용해 실 Postgres 없이 테스트한다.
db_session fixture 는 conftest.py 에서 제공한다.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import DataSettings, NotificationSettings, ThemeSettings, UserSettingsPatch
from app.services import user_settings as svc


class TestDefaultFactory:
    def test_default_has_expected_fields(self) -> None:
        s = svc.default_settings("u1")
        assert s.user_id == "u1"
        assert s.name == "Demo User"
        assert s.email == "demo@demo.com"
        assert s.language == "ko"
        assert s.timezone == "Asia/Seoul"
        assert s.theme.mode == "system"
        assert s.theme.accent == "violet"
        assert s.notifications.email_alerts is True
        assert s.data.refresh_interval_sec == 60
        assert len(s.connected_accounts) >= 1
        assert s.updated_at  # ISO 문자열 존재

    def test_default_idempotent_different_users(self) -> None:
        s1 = svc.default_settings("u1")
        s2 = svc.default_settings("u2")
        assert s1.user_id == "u1"
        assert s2.user_id == "u2"


class TestGetSettings:
    @pytest.mark.asyncio
    async def test_get_creates_default_on_first_call(self, db_session: AsyncSession) -> None:
        s = await svc.get_settings(db_session, "new-user")
        assert s.user_id == "new-user"

    @pytest.mark.asyncio
    async def test_get_returns_same_instance_on_second_call(self, db_session: AsyncSession) -> None:
        s1 = await svc.get_settings(db_session, "u1")
        s2 = await svc.get_settings(db_session, "u1")
        # 두 번째 호출은 SELECT only — updated_at 동일
        assert s1.updated_at == s2.updated_at

    @pytest.mark.asyncio
    async def test_get_independent_per_user(self, db_session: AsyncSession) -> None:
        s1 = await svc.get_settings(db_session, "u1")
        s2 = await svc.get_settings(db_session, "u2")
        assert s1.user_id != s2.user_id


class TestPatchSettings:
    @pytest.mark.asyncio
    async def test_empty_patch_does_not_change_values(self, db_session: AsyncSession) -> None:
        original = await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(db_session, "u1", UserSettingsPatch())
        assert patched.name == original.name
        assert patched.language == original.language
        assert patched.timezone == original.timezone

    @pytest.mark.asyncio
    async def test_empty_patch_updates_updated_at(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(db_session, "u1", UserSettingsPatch())
        # updated_at 은 ISO 문자열이 존재해야 한다
        assert patched.updated_at

    @pytest.mark.asyncio
    async def test_patch_name_only(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(db_session, "u1", UserSettingsPatch(name="Alice"))
        assert patched.name == "Alice"
        assert patched.language == "ko"  # 변경 안 됨

    @pytest.mark.asyncio
    async def test_patch_language(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(db_session, "u1", UserSettingsPatch(language="en"))
        assert patched.language == "en"

    @pytest.mark.asyncio
    async def test_patch_timezone(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(
            db_session, "u1", UserSettingsPatch(timezone="America/New_York")
        )
        assert patched.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_nested_theme_patch(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(
            db_session,
            "u1",
            UserSettingsPatch(theme=ThemeSettings(mode="dark", accent="cyan")),
        )
        assert patched.theme.mode == "dark"
        assert patched.theme.accent == "cyan"

    @pytest.mark.asyncio
    async def test_nested_notifications_patch(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(
            db_session,
            "u1",
            UserSettingsPatch(notifications=NotificationSettings(email_alerts=False)),
        )
        assert patched.notifications.email_alerts is False
        assert patched.notifications.push_alerts is False  # 기본값 유지

    @pytest.mark.asyncio
    async def test_full_patch(self, db_session: AsyncSession) -> None:
        await svc.get_settings(db_session, "u1")
        patched = await svc.patch_settings(
            db_session,
            "u1",
            UserSettingsPatch(
                name="Bob",
                language="en",
                timezone="UTC",
                theme=ThemeSettings(mode="light", accent="rose"),
                notifications=NotificationSettings(push_alerts=True, price_threshold_pct=10.0),
                data=DataSettings(refresh_interval_sec=30, auto_backup=True),
            ),
        )
        assert patched.name == "Bob"
        assert patched.language == "en"
        assert patched.timezone == "UTC"
        assert patched.theme.mode == "light"
        assert patched.notifications.push_alerts is True
        assert patched.data.refresh_interval_sec == 30
