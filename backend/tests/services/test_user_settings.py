"""User Settings 서비스 단위 테스트 — migration 006: DB 기반.

SQLite in-memory DB 를 사용해 실 Postgres 없이 테스트한다.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_settings_returns_default_when_not_exists(db_session: AsyncSession) -> None:
    """DB 에 행이 없으면 기본값으로 INSERT 후 반환."""
    from app.services.user_settings import get_settings

    result = await get_settings(db_session, "new-user-abc")

    assert result.user_id == "new-user-abc"
    assert result.language == "ko"
    assert result.timezone == "Asia/Seoul"
    assert result.theme.mode == "system"
    assert result.theme.accent == "violet"
    assert result.notifications.email_alerts is True
    assert result.data.refresh_interval_sec == 60
    assert len(result.connected_accounts) == 1
    assert result.connected_accounts[0].provider == "google"


@pytest.mark.asyncio
async def test_get_settings_returns_existing_row(db_session: AsyncSession) -> None:
    """DB 에 행이 있으면 조회 결과를 그대로 반환 (중복 INSERT 없음)."""
    from app.services.user_settings import get_settings

    # 최초 호출 — INSERT
    first = await get_settings(db_session, "existing-user")
    # 두 번째 호출 — SELECT only
    second = await get_settings(db_session, "existing-user")

    assert first.user_id == second.user_id
    assert first.language == second.language


@pytest.mark.asyncio
async def test_patch_settings_updates_language(db_session: AsyncSession) -> None:
    """language 패치 후 DB 에서 'en' 으로 반환되어야 한다."""
    from app.schemas.user import UserSettingsPatch
    from app.services.user_settings import get_settings, patch_settings

    # 초기 행 생성
    await get_settings(db_session, "patch-user")

    patch = UserSettingsPatch(language="en")
    result = await patch_settings(db_session, "patch-user", patch)

    assert result.language == "en"
    # 다른 필드는 기본값 유지
    assert result.timezone == "Asia/Seoul"


@pytest.mark.asyncio
async def test_patch_settings_deep_merges_theme(db_session: AsyncSession) -> None:
    """theme 패치 시 mode 만 변경 — accent 기본값 유지."""
    from app.schemas.user import ThemeSettings, UserSettingsPatch
    from app.services.user_settings import get_settings, patch_settings

    await get_settings(db_session, "theme-user")

    patch = UserSettingsPatch(theme=ThemeSettings(mode="dark", accent="violet"))
    result = await patch_settings(db_session, "theme-user", patch)

    assert result.theme.mode == "dark"
    assert result.theme.accent == "violet"


@pytest.mark.asyncio
async def test_patch_settings_creates_row_if_not_exists(db_session: AsyncSession) -> None:
    """행이 없을 때 patch_settings 를 직접 호출해도 기본값 INSERT 후 패치 적용."""
    from app.schemas.user import UserSettingsPatch
    from app.services.user_settings import patch_settings

    patch = UserSettingsPatch(language="en", timezone="UTC")
    result = await patch_settings(db_session, "new-patch-user", patch)

    assert result.user_id == "new-patch-user"
    assert result.language == "en"
    assert result.timezone == "UTC"
    # 패치하지 않은 theme 은 기본값
    assert result.theme.mode == "system"


@pytest.mark.asyncio
async def test_patch_settings_updated_at_advances(db_session: AsyncSession) -> None:
    """PATCH 호출 후 updated_at 이 이전 값보다 같거나 늦어야 한다."""
    from app.schemas.user import UserSettingsPatch
    from app.services.user_settings import get_settings, patch_settings

    original = await get_settings(db_session, "ts-user")
    original_ts = original.updated_at

    patch = UserSettingsPatch(language="en")
    updated = await patch_settings(db_session, "ts-user", patch)

    # updated_at 은 ISO 문자열 — 사전순 비교로 시간 증가 확인
    assert updated.updated_at >= original_ts


@pytest.mark.asyncio
async def test_patch_settings_notifications_deep_merge(db_session: AsyncSession) -> None:
    """notifications 패치 시 지정 필드만 변경, 나머지는 기본값 유지."""
    from app.schemas.user import NotificationSettings, UserSettingsPatch
    from app.services.user_settings import get_settings, patch_settings

    await get_settings(db_session, "notif-user")

    patch = UserSettingsPatch(
        notifications=NotificationSettings(
            email_alerts=False,
            push_alerts=False,
            price_threshold_pct=5.0,
            daily_digest=True,
        )
    )
    result = await patch_settings(db_session, "notif-user", patch)

    assert result.notifications.email_alerts is False
    assert result.notifications.daily_digest is True


@pytest.mark.asyncio
async def test_user_isolation(db_session: AsyncSession) -> None:
    """서로 다른 user_id 설정이 독립적으로 저장된다."""
    from app.schemas.user import UserSettingsPatch
    from app.services.user_settings import get_settings, patch_settings

    await get_settings(db_session, "user-a")
    await get_settings(db_session, "user-b")

    await patch_settings(db_session, "user-a", UserSettingsPatch(language="en"))

    user_a = await get_settings(db_session, "user-a")
    user_b = await get_settings(db_session, "user-b")

    assert user_a.language == "en"
    assert user_b.language == "ko"  # user-b 는 영향 없음
