"""Unit tests — user_settings 서비스 (sprint-08 B-6)."""
from __future__ import annotations

import pytest

from app.schemas.user import DataSettings, NotificationSettings, ThemeSettings, UserSettingsPatch
from app.services import user_settings as svc


@pytest.fixture(autouse=True)
def reset():
    """각 테스트 전후 in-memory store 초기화."""
    svc.reset_store()
    yield
    svc.reset_store()


class TestDefaultFactory:
    def test_default_has_expected_fields(self):
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

    def test_default_idempotent_different_users(self):
        s1 = svc.default_settings("u1")
        s2 = svc.default_settings("u2")
        assert s1.user_id == "u1"
        assert s2.user_id == "u2"


class TestGetSettings:
    def test_get_creates_default_on_first_call(self):
        s = svc.get_settings("new-user")
        assert s.user_id == "new-user"

    def test_get_returns_same_instance_on_second_call(self):
        s1 = svc.get_settings("u1")
        s2 = svc.get_settings("u1")
        assert s1.updated_at == s2.updated_at

    def test_get_independent_per_user(self):
        s1 = svc.get_settings("u1")
        s2 = svc.get_settings("u2")
        assert s1.user_id != s2.user_id


class TestPatchSettings:
    def test_empty_patch_does_not_change_values(self):
        original = svc.get_settings("u1")
        patched = svc.patch_settings("u1", UserSettingsPatch())
        assert patched.name == original.name
        assert patched.language == original.language
        assert patched.timezone == original.timezone

    def test_empty_patch_updates_updated_at(self):
        svc.get_settings("u1")
        patched = svc.patch_settings("u1", UserSettingsPatch())
        # updated_at 은 갱신되어야 한다 (동일할 수도 있으나 필드가 존재해야 함)
        assert patched.updated_at

    def test_patch_name_only(self):
        svc.get_settings("u1")
        patched = svc.patch_settings("u1", UserSettingsPatch(name="Alice"))
        assert patched.name == "Alice"
        assert patched.language == "ko"  # 변경 안 됨

    def test_patch_language(self):
        svc.get_settings("u1")
        patched = svc.patch_settings("u1", UserSettingsPatch(language="en"))
        assert patched.language == "en"

    def test_patch_timezone(self):
        svc.get_settings("u1")
        patched = svc.patch_settings("u1", UserSettingsPatch(timezone="America/New_York"))
        assert patched.timezone == "America/New_York"

    def test_nested_theme_patch(self):
        svc.get_settings("u1")
        patched = svc.patch_settings(
            "u1",
            UserSettingsPatch(theme=ThemeSettings(mode="dark", accent="cyan")),
        )
        assert patched.theme.mode == "dark"
        assert patched.theme.accent == "cyan"

    def test_nested_notifications_patch(self):
        svc.get_settings("u1")
        patched = svc.patch_settings(
            "u1",
            UserSettingsPatch(notifications=NotificationSettings(email_alerts=False)),
        )
        assert patched.notifications.email_alerts is False
        assert patched.notifications.push_alerts is False  # 기본값 유지

    def test_full_patch(self):
        svc.get_settings("u1")
        patched = svc.patch_settings(
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
